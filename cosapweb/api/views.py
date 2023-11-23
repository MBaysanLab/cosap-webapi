import base64
import json
import mimetypes
import os
import re
import tempfile
from multiprocessing.pool import ThreadPool
from pathlib import Path
from urllib import request
from wsgiref.util import FileWrapper

import pysam
from django.contrib.auth import get_user_model
from django.core import serializers as django_serializers
from django.db.models import Q
from django.db.models.query import QuerySet
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django_drf_filepond.parsers import PlainTextParser, UploadChunkParser
from django_drf_filepond.renderers import PlainTextRenderer
from django_drf_filepond.views import PatchView, ProcessView
from rest_framework import mixins, permissions, status, views, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.decorators import api_view

from cosapweb.api import serializers
from cosapweb.api.models import (SNV, Action, File, Project, ProjectFiles,
                                 ProjectSNVData, ProjectSNVs, ProjectSummary,
                                 ProjectTask)
from cosapweb.api.permissions import IsOwnerOrDoesNotExist, OnlyAdminToList

from ..common.utils import (convert_file_relative_path_to_absolute_path,
                            create_chonky_filemap, get_project_dir,
                            get_user_dir)
from .celery_handlers import submit_cosap_dna_job

USER = get_user_model()


class UserViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    View to list (admins only), view and update user information.
    """

    permission_classes = [
        permissions.IsAuthenticated,
        IsOwnerOrDoesNotExist,
        OnlyAdminToList,
    ]

    lookup_field = "email"
    serializer_class = serializers.UserSerializer
    queryset = USER.objects.all()


class VerifyUserVeiwSet(viewsets.ViewSet):
    """
    View to verify user with token and get email.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.UserSerializer
    queryset = USER.objects.all()

    def create(self, request):
        token = (
            request.headers["Authorization"].split()[1]
            if "Authorization" in request.headers
            else None
        )

        if token and Token.objects.filter(key=token).exists():
            user = Token.objects.get(key=token).user
            user_serializer = self.serializer_class(user)
            return Response(user_serializer.data, status=status.HTTP_200_OK)

        return Response(status=status.HTTP_404_NOT_FOUND)

    def update(self, request):
        """
        Change password
        """
        request_token = (
            request.headers["Authorization"].split()[1]
            if "Authorization" in request.headers
            else None
        )

        if request_token and Token.objects.filter(key=request_token).exists():
            user = Token.objects.get(key=request_token).user
            if user.check_password(request.data["old_password"]):
                user.set_password(request.data["new_password"])
                user.save()
                return Response(status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
        return Response(status=status.HTTP_404_NOT_FOUND)


class AuthTokenViewSet(ObtainAuthToken, viewsets.ViewSet):
    """
    View to get auth token given username and password.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RegisterViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    View to register a user (also logs the user in).
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    queryset = USER.objects.all()
    serializer_class = serializers.RegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        user = USER.objects.get(id=serializer.instance.id)

        token = Token.objects.get(user=user)
        return Response({"token": token.key})


class ProjectViewSet(viewsets.ModelViewSet):
    """
    View to create, view, update and list projects where the requesting user is the creator or a collaborator.
    """

    permission_classes = [permissions.IsAuthenticated]

    queryset = Project.objects.order_by("-created_at")
    serializer_class = serializers.ProjectSerializer

    def get_queryset(self):
        """
        Get the list of items for this view.

        Overridden only to return projects where the requesting user
        is the creator of the project or a collaborator in the project.
        """
        queryset = self.queryset
        if isinstance(queryset, QuerySet):
            user = self.request.user
            if user.is_superuser:
                return queryset
            queryset = queryset.filter(Q(user=user) | Q(collaborators=user) | Q(is_demo=True))
        return queryset

    def create(self, request, *args, **kwargs):
        user = request.user
        project_type = request.POST.get("project_type")
        name = request.POST.get("name")
        algorithms = json.loads(request.POST.get("algorithms"))
        new_project = Project.objects.create(
            user=user,
            project_type=project_type,
            name=name,
            algorithms=algorithms,
            status="PENDING",
        )

        normal_file_ids = json.loads(request.POST.get("normal_files", "[]"))
        tumor_file_ids = json.loads(request.POST.get("tumor_files", "[]"))
        bed_file_ids = json.loads(request.POST.get("bed_files", "[]"))

        project_files = ProjectFiles.objects.create(project=new_project)

        for file_id in normal_file_ids:
            file = File.objects.get(uuid=file_id)
            project_files.files.add(file)

        for file_id in tumor_file_ids:
            file = File.objects.get(uuid=file_id)
            project_files.files.add(file)

        for file_id in bed_file_ids:
            file = File.objects.get(uuid=file_id)
            project_files.files.add(file)

        project_files.save()

        # Create project directory under user directory
        user_dir = get_user_dir(user)
        project_dir = os.path.join(user_dir, f"{new_project.id}_{new_project.name}")
        os.makedirs(project_dir)
        try:
            pool = ThreadPool(processes=1)
            async_result = pool.apply_async(submit_cosap_dna_job, (new_project.id,))
            task_id = async_result.get()
            ProjectTask.objects.create(project=new_project, task_id=task_id)

        except Exception as e:
            print(f"Error submitting job: {e}")
            # new_project.status = "FAILED"
            # new_project.save()

        return HttpResponse(status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk):
        project = Project.objects.get(id=pk)

        project_metadata = {
            "name": project.name,
            "status": project.status,
            "collaborators": ",".join(
                [col.email for col in project.collaborators.all()]
            ),
            "time": project.created_at,
        }

        results = ProjectSummary.objects.get(project=project)

        return Response(
            {
                "metadata": project_metadata,
                "summary": model_to_dict(results),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def rerun_project(self, request, pk=None):
        project = Project.objects.get(id=pk)
        project.status = "PENDING"
        project.save()

        try:
            pool = ThreadPool(processes=1)
            async_result = pool.apply_async(submit_cosap_dna_job, (project.id,))
            task_id = async_result.get()
            ProjectTask.objects.create(project=project, task_id=task_id)

        except Exception as e:
            print(f"Error submitting job: {e}")
            project.status = "FAILED"
            project.save()

        return HttpResponse(status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def delete_project(self, request, pk=None):
        project = Project.objects.get(id=pk)
        project.delete()
        return HttpResponse(status=status.HTTP_200_OK)


class ProjectSNVViewset(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        project = Project.objects.get(id=pk)
        project_snvs = ProjectSNVs.objects.get(project=project)

        all_variants = []
        for snv in project_snvs.snvs.all():
            variant_dict = model_to_dict(snv)
            try:
                variant_dict["af"] = ProjectSNVData.objects.get(
                    project=project, snv=snv
                ).allele_frequency
            except Exception as e:
                variant_dict["af"] = -1

            all_variants.append(variant_dict)

        return Response(all_variants)


class IGVDataView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def ranged_data_response(self, range_header, path):
        if not range_header:
            return None
        m = re.search("(\d+)-(\d*)", range_header)
        if not m:
            return "Error: unexpected range header syntax: {}".format(range_header)

        size = os.path.getsize(path)
        offset = int(m.group(1))
        length = int(m.group(2) or size) - offset + 1

        data = None
        with open(path, "rb") as f:
            f.seek(offset)
            data = f.read(length)

        response = HttpResponse(
            data,
            headers={
                "Content-Range": f"bytes {offset}-{offset + length - 1}/{size}",
            },
            content_type="application/octet-stream",
        )
        response.status_code = 206

        return response

    def get(self, request, b64_string):
        decoded_path = base64.b64decode(b64_string).decode("utf-8")

        if decoded_path.endswith(".bai"):
            return FileViewSet().download(request, b64_string)

        file_path = convert_file_relative_path_to_absolute_path(decoded_path)

        if not os.path.exists(file_path):
            raise Http404

        range_header = request.headers.get("Range")
        return self.ranged_data_response(range_header, file_path)


class ActionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    queryset = Action.objects.order_by("-created_at")
    serializer_class = serializers.ActionSerializer

    def get_queryset(self):
        """
        Get the list of items for this view.

        Overridden to only return projects where the requesting user
        is the creator of the project or a collaborator in the project.
        """
        queryset = self.queryset

        if isinstance(queryset, QuerySet):
            user = self.request.user
            queryset = queryset.filter(Q(associated_user=user))
        return queryset


class FileViewSet(ProcessView, PatchView, viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, UploadChunkParser)
    renderer_classes = (PlainTextRenderer, JSONRenderer)

    def list(self, request, project_id=None):
        return_type = request.GET.get("return_type")
        sample_type = (
            request.GET.get("sample_type").upper()
            if request.GET.get("sample_type")
            else None
        )
        file_type = (
            request.GET.get("file_type").upper()
            if request.GET.get("file_type")
            else None
        )

        if return_type and (return_type == "projectFileMap"):
            project = Project.objects.get(id=project_id)

            if not project:
                return Response(status=status.HTTP_404_NOT_FOUND)

            project_dir = get_project_dir(project)
            files = create_chonky_filemap(project_dir, project.name)
            return Response(files)

        if sample_type:
            files = File.objects.filter((Q(user=request.user) | Q(is_demo=True)), Q(sample_type=sample_type))
            files = {
                files[i].uuid: f"{i+1} - {files[i].name}" for i in range(len(files))
            }
            return Response(files)

        if file_type:
            files = {
                file.uuid: f"{file.project.name} - {file.name}"
                for file in File.objects.filter((Q(user=request.user) | Q(is_demo=True)), Q(file_type=file_type))
            }
            return Response(files)

        files = [file.filename for file in File.objects.filter(Q(user=request.user) | Q(is_demo=True))]
        return Response(files)

    def create(self, request, *args, **kwargs):
        if request.FILES.get("file"):
            filename = request.FILES.get("file").name
            sample_type = request.POST.get("sample_type")
            file = request.FILES.get("file")
            user = request.user
            f = File.objects.create(
                name=filename, user=user, file=file, sample_type=sample_type
            )
            f.save()
            return Response(str(f.uuid))
        else:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                temp_id = response.data
                sample_type = request.POST.get("sample_type")
                f = File.objects.create(
                    user=request.user, uuid=temp_id, sample_type=sample_type
                )
            return response

    def download(self, request, b64_string):
        decoded_path = base64.b64decode(b64_string).decode("utf-8")
        file_path = convert_file_relative_path_to_absolute_path(decoded_path)

        if not os.path.exists(file_path):
            raise Http404

        filename = os.path.basename(file_path)
        response = StreamingHttpResponse(
            FileWrapper(
                open(file_path, "rb"),
            ),
            content_type="application/octet-stream",
        )
        response["Content-Length"] = os.path.getsize(file_path)
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
