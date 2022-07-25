from django.contrib.auth.models import User
from rest_framework import serializers

from cosapweb.api.models import Organization


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
