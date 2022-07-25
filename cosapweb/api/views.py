from django.contrib.auth.models import User
from rest_framework import mixins, permissions, viewsets

from cosapweb.api import serializers
from cosapweb.api.permissions import IsOwnerOrDoesNotExist, OnlyAdminToList


class UserViewSet(mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):

    permission_classes = [permissions.IsAuthenticated,
                          IsOwnerOrDoesNotExist, OnlyAdminToList]

    queryset = User.objects.all()
    lookup_field = "username"
    serializer_class = serializers.UserSerializer
