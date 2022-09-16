from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db.models.query import QuerySet
from rest_framework import mixins, permissions, views, viewsets
from rest_framework.response import Response
from cosapweb.api import serializers
from cosapweb.api.models import Project, Sample, Action
from cosapweb.api.permissions import IsOwnerOrDoesNotExist, OnlyAdminToList



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



class RegisterViewSet(mixins.CreateModelMixin,
                      viewsets.GenericViewSet):
    """
    View to register a user (also logs the user in).
    """
    permission_classes = [permissions.AllowAny]

    queryset = USER.objects.all()
    serializer_class = serializers.RegistrationSerializer


class LoginViewSet(mixins.CreateModelMixin,
                   viewsets.GenericViewSet):
    """
    View to login.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.LoginSerializer

    # Override POST request handler
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return Response()


class LogoutView(views.APIView):
    """
    View to logout.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        logout(request)
        return Response()


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