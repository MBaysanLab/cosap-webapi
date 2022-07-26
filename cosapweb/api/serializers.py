from django.contrib.auth.models import User
from rest_framework import serializers

from cosapweb.api.models import Organization, Project


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "country", "address"]


class UserSerializer(serializers.HyperlinkedModelSerializer):
    # TODO: A user should be allowed to remove or add a relationship to an org.
    organizations = OrganizationSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ["url", "username", "first_name", "last_name", "email",
                  "last_login", "date_joined", "organizations"]
        read_only_fields = ["last_login", "date_joined"]
        extra_kwargs = {
            'url': {'lookup_field': 'username'},
        }


class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    creator = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True
    )
    collaborators = serializers.SlugRelatedField(
        many=True,
        slug_field='username',
        queryset=User.objects.all()
    )

    # Use human readable names instead of actual values in the status field
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.get_status_display()

    class Meta:
        model = Project
        fields = ["url", "id", "name", "project_type", "status",
                  "percentage", "creator", "created_at", "collaborators"]
        read_only_fields = ["created_at", "status", "percentage"]
        extra_kwargs = {
            'collaborators': {'lookup_field': 'username'},
        }
