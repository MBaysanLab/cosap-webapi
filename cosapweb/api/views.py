import os
from urllib import request

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.models.query import QuerySet
from rest_framework import mixins, permissions, status, viewsets, views
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from django.http import HttpResponse, StreamingHttpResponse, Http404

from cosapweb.api import serializers
from cosapweb.api.models import Action, File, Project
from cosapweb.api.permissions import IsOwnerOrDoesNotExist, OnlyAdminToList
from ..common.utils import run_parse_project_data, get_user_dir
import mimetypes
from wsgiref.util import FileWrapper
from pathlib import Path
import pysam


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

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status="IP")

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
        project_data = run_parse_project_data(
            "/home/mae/Desktop/cosap-webapi/data/1_arif0241@hotmail.com/105_api_test"
        )
        return Response(
            {
                "metadata": project_metadata,
                "coverage_stats": {
                    "mean_coverage": project_data["qc_results"]["mean_coverage"],
                    "coverage_hist": project_data["qc_coverage_histogram"][
                        "hist"
                    ].items(),
                },
                "mapping_stats": {
                    "percetange_of_mapped_reads": project_data["qc_results"][
                        "percentage_aligned"
                    ]
                },
                "variant_stats": project_data["variant_stats"],
                "variants": project_data["variants"],
            }
        )


class FileViewSet(viewsets.ModelViewSet):
    """
    View to create, view, update and list samples.
    """

    permission_classes = [permissions.IsAuthenticated]

    queryset = File.objects.order_by("-uploaded_at")
    serializer_class = serializers.FileSerializer

    def get_queryset(self):
        """
        Get the list of items for this view.

        Overridden to only return samples for projects where the requesting
        user is the creator of the project or a collaborator in the project.
        """
        queryset = self.queryset
        if isinstance(queryset, QuerySet):
            user = self.request.user
            queryset = queryset.filter(
                Q(project__user=user) | Q(project__collaborators=user)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


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
