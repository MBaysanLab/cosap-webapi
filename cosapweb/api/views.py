from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.query import QuerySet
from rest_framework import mixins, permissions, viewsets

from cosapweb.api import serializers
from cosapweb.api.models import Project
from cosapweb.api.permissions import IsOwnerOrDoesNotExist, OnlyAdminToList


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

    queryset = User.objects.all()
    lookup_field = "username"
    serializer_class = serializers.UserSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    """
    View to create, view, update and list projects where the requesting user is the creator or a collaborator.
    """

    permission_classes = [permissions.IsAuthenticated]

    queryset = Project.objects.all()
    serializer_class = serializers.ProjectSerializer

    def get_queryset(self):
        """
            Get the list of items for this view.

            Overridden to only return projects where the requesting user
            is the creator of the project or a collaborator.
        """
        queryset = self.queryset
        if isinstance(queryset, QuerySet):
            # Ensure queryset is re-evaluated on each request.
            queryset = queryset.filter(
                Q(creator__username=self.request.user.username) |
                Q(collaborators__username=self.request.user.username))
        return queryset

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user, status="ON")
