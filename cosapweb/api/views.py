import json
import mimetypes
import os
import tempfile
from multiprocessing.pool import ThreadPool
from pathlib import Path
from urllib import request
from wsgiref.util import FileWrapper

import pysam
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.models.query import QuerySet
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponse, StreamingHttpResponse, FileResponse
from django.core import serializers as django_serializers
from django_drf_filepond.parsers import PlainTextParser, UploadChunkParser
from django_drf_filepond.renderers import PlainTextRenderer
from django_drf_filepond.views import PatchView, ProcessView
from rest_framework import mixins, permissions, status, views, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from cosapweb.api import serializers
from cosapweb.api.createpdf import create_pdf

from cosapweb.api.models import (
    Action,
    File,
    Project,
    ProjectFile,
    ProjectTask,
    ProjectVariant,
    Variant,
)
from cosapweb.api.permissions import IsOwnerOrDoesNotExist, OnlyAdminToList

from ..common.utils import get_user_dir
from .celery_handlers import submit_cosap_dna_job

USER = get_user_model()
class VariantFeaturesPdfViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    def create(self, request):
        variant_ids = request.data.get('ids', [])

        if not variant_ids:
            return Response({'detail': 'No variant_ids provided'}, status=status.HTTP_400_BAD_REQUEST)

        variants = Variant.objects.filter(id__in=variant_ids)

        if not variants.exists():
            return Response({'detail': 'No variants found for given IDs in the specified project'}, status=status.HTTP_404_NOT_FOUND)

        # Collect all variants from the ProjectVariants

        # Convert variants to dictionaries
        variants_dict = [model_to_dict(variant) for variant in variants]

        # Create pdf from variants data. You will have to implement this yourself.
        pdf_path = create_pdf(variants_dict)

        if not pdf_path:
            return Response({'detail': 'Failed to create PDF'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Report.pdf"'

        return response


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
            print(e)
            new_project.status = "FAILED"
            new_project.save()

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

        return Response(
            {
                "metadata": project_metadata,
                "coverage_stats": {"mean_coverage": 152, "coverage_hist": []},
                "mapping_stats": {"percetange_of_mapped_reads": 99.21},
                "msi_stats": {"msi_score": 0.32},
                "cnv_stats": {"total_cnvs": 6},
                "variant_stats": {
                    "total_variants": 8313,
                    "significant_variants": 1,
                    "uncertain_variants": 803,
                },
            }
        )


class ProjectVariantViewset(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        project = Project.objects.get(id=pk)
        pv = ProjectVariant.objects.get(project=project)
        variants = [model_to_dict(variant) for variant in pv.variants.all()][:10]
        return Response(variants)


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

class VairantDetailViewSet(viewsets.ModelViewSet):

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

    def retrieve(self, request,pk):

        transcriptText = "Clicked " + pk + ". variant"

        response_data = {
            "overview": {
                "depthMin": "50",
                "depthMax": "200",
                "depthValue": "85",
                "runPercent": "100",
                "transcriptText": transcriptText,
                "cDNAText": "c.129",
                "accountPercent": "100",
                "varFraction": "75",
                "sequenceFirstText": "ABCD",
                "sequenceSecondText": "D",
                "refAltFirstText": "ABCD",
                "refAltSecondText": "C",
                "aminoacidFirstText": "QWERT",
                "aminoacidSecondText": "T",
                "communityPercent": "100",
                "proteinText": "protein1"
            },
            "details": {
                "aliasesTags": ["Allies1", "Allies2", "Allies3", "Allies4", "Allies5"],
                "variantTypesTags": ["var1", "var2", "var3"],
                "hgvsTags": ["HGVS", "HGVS", "HGVS"],
                "maneTags": ["MAne1", "MAne1", "MAne1"],
                "geneTag": [pk],
                "alleleRegistryTag": ["2"],
                "clinTag": ["x2"],
                "openCRAVATTag": ["x3"],
                "transcriptTag": ["ens12"],
                "refBuildValue": "gr",
                "enssemblyVersionValue": "75",
                "chrValue": "9",
                "startValue": "3",
                "stopValue": "3",
                "refBasesValue": "A"
            }
        }

        return Response(response_data)