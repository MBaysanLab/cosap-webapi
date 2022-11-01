from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db.models.query import QuerySet
from rest_framework import mixins, permissions, views, viewsets
from rest_framework.response import Response
from rest_framework import status
from cosapweb.api import serializers
from cosapweb.api.models import Project, Sample, Action
from cosapweb.api.permissions import IsOwnerOrDoesNotExist, OnlyAdminToList
from rest_framework.authtoken.models import Token


USER = get_user_model()

class UserViewSet(mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    """
    View to list (admins only), view and update user information.
    """

    permission_classes = [permissions.IsAuthenticated,
                          IsOwnerOrDoesNotExist, OnlyAdminToList]

    lookup_field = "email"
    serializer_class = serializers.UserSerializer
    queryset = USER.objects.all()


class GetUserView(views.APIView):
    """
    View to authorize user with token.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        request_token = request.headers["Authorization"].split()[1]

        if Token.objects.filter(key=request_token).exists():
            user = Token.objects.get(key=request_token).user
            return Response({"user":user.email}, status=status.HTTP_200_OK)

        return Response(status=status.HTTP_401_UNAUTHORIZED)


class RegisterViewSet(mixins.CreateModelMixin,
                      viewsets.GenericViewSet):
    """
    View to register a user (also logs the user in).
    """

    permission_classes = [permissions.AllowAny]

    queryset = USER.objects.all()
    serializer_class = serializers.RegistrationSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    """
    View to create, view, update and list projects where the requesting user is the creator or a collaborator.
    """

    permission_classes = [permissions.IsAuthenticated]

    queryset = Project.objects.order_by('-created_at')
    serializer_class = serializers.ProjectSerializer

    def get_queryset(self):
        """
            Get the list of items for this view.

            Overridden to only return projects where the requesting user
            is the creator of the project or a collaborator in the project.
        """
        queryset = self.queryset
        if isinstance(queryset, QuerySet):
            user = self.request.user
            queryset = queryset.filter(Q(creator=user) | Q(collaborators=user))
        return queryset

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user, status="ON")


class SampleViewSet(viewsets.ModelViewSet):
    """
    View to create, view, update and list samples.
    """

    permission_classes = [permissions.IsAuthenticated]

    queryset = Sample.objects.order_by('-uploaded_at')
    serializer_class = serializers.SampleSerializer

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
                Q(project__creator=user) | Q(project__collaborators=user))
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ActionViewSet(viewsets.ModelViewSet):

    permission_classes = [permissions.IsAuthenticated]
    
    queryset = Action.objects.order_by('-created')
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