import json
import mimetypes
import os
import tempfile
from pathlib import Path
from urllib import request
from wsgiref.util import FileWrapper

import pysam
from django.contrib.auth import get_user_model
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
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from cosapweb.api import serializers
from cosapweb.api.models import (
    Action,
    File,
    Project,
    ProjectFile,
    ProjectVariant,
    Variant,
)
from cosapweb.api.permissions import IsOwnerOrDoesNotExist, OnlyAdminToList

from ..common.utils import get_user_dir, run_parse_project_data

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


class GetUserViewSet(viewsets.ViewSet):
    """
    View to verify user with token and get email.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        request_token = (
            request.headers["Authorization"].split()[1]
            if "Authorization" in request.headers
            else None
        )

        if request_token and Token.objects.filter(key=request_token).exists():
            user = Token.objects.get(key=request_token).user
            return Response({"user": user.email}, status=status.HTTP_200_OK)

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
            queryset = queryset.filter(Q(user=user) | Q(collaborators=user))
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

        normal_file_ids = json.loads(request.POST.get("normal_files"))
        tumor_file_ids = json.loads(request.POST.get("tumor_files"))
        bed_file_ids = json.loads(request.POST.get("bed_files"))

        project_files = ProjectFile.objects.create(project=new_project)

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

        return HttpResponse(status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk):
        project = Project.objects.get(id=pk)
        file_obj = File.objects.filter(project=project).first()
        file_path, _ = os.path.split(file_obj.file.name)

        project_metadata = {
            "name": project.name,
            "status": project.status,
            "collaborators": ",".join(
                [col.email for col in project.collaborators.all()]
            ),
            "time": project.created_at,
        }

        print("Querying variants...")
        pv = ProjectVariant.objects.filter(project=project)
        print("Querying variants...done")
        variants = [model_to_dict(pvv.variant) for pvv in pv][:100]
        print("Converting variants...done")
        variants_json = json.dumps(variants)

        return Response(
            {
                "metadata": project_metadata,
                "coverage_stats": {"mean_coverage": 152, "coverage_hist": []},
                "mapping_stats": {"percetange_of_mapped_reads": 99.21},
                "variant_stats": {
                    "total_variants": 8313,
                    "significant_variants": 1,
                    "uncertain_variants": 803,
                },
                "variants": variants,
            }
        )


class FileDownloadView(views.APIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, path, *args, **kwargs):
        user = request.user
        user_dir = get_user_dir(user)
        file_path = os.path.join(user_dir, path)

        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            response = StreamingHttpResponse(
                FileWrapper(
                    open(file_path, "rb"),
                ),
                content_type=mimetypes.guess_type(file_path)[0],
            )
            response["Content-Length"] = os.path.getsize(file_path)
            response["Content-Disposition"] = f"attachment; filename={filename}"
            return response
        raise Http404


class AligmentLoadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def build_view_args(filename, region, reference=None, optionArray=None):
        args = []

        if optionArray:
            args.extend(optionArray)

        if reference:
            args.append("-T")
            args.append(reference)

        args.append(filename)

        if region:
            args.append(region)

        return args

    def get(self, request, path):
        user = request.user
        user_dir = get_user_dir(user)
        file_path = os.path.join(user_dir, path)
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            response = StreamingHttpResponse(
                pysam.view(file_path, "chr1:1040655-1040695"),
                content_type=mimetypes.guess_type(file_path)[0],
            )
            response["Content-Disposition"] = f"attachment; filename=calibrated.sam"
            return response
        raise Http404


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
    renderer_classes = (PlainTextRenderer,)

    def list(self, request):
        files = [file.filename for file in File.objects.filter(user=request.user)]
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

    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
