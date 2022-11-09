from django.contrib.auth import (authenticate, get_user_model, password_validation)
from rest_framework import serializers

from cosapweb.api.models import Action, Affiliation, File, Project
from rest_framework.authtoken.models import Token

USER = get_user_model()


class AffiliationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Affiliation
        fields = ["id", "name", "country", "address"]


class UserSerializer(serializers.ModelSerializer):
    # TODO: A user should be allowed to remove or add a relationship to an org.
    affiliations = AffiliationSerializer(many=True, read_only=True)

    class Meta:
        model = USER
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "last_login",
            "date_joined",
            "Affiliations",
        ]
        read_only_fields = ["last_login", "date_joined"]


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = USER
        fields = [
            "pk",
            "password",
            "first_name",
            "last_name",
            "email",
            "affiliations",
        ]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
            "affiliations": {"required": False}
        }

    def create(self, data):
        if USER.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError("Email already exist")

        user = USER.objects.create(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            password=data["password"]
        )
        
        return user


class FileSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        read_only=True,
        slug_field="email",
    )

    class Meta:
        model = File
        fields = ["id", "project", "user", "name", "file_type", "file", "uploaded_at"]
        read_only_fields = ["uploaded_at"]

    def validate(self, attrs):
        # Users can add samples only to projects they have access to
        user = self.context.get("request").user
        project = attrs["project"]
        if project.creator != user and project not in Project.objects.filter(
            collaborators=user
        ):
            raise serializers.ValidationError(
                {"project": "You don't have access to this project!"}
            )

        return attrs


class ProjectSerializer(serializers.ModelSerializer):
    creator = serializers.SlugRelatedField(slug_field="email", read_only=True)
    collaborators = serializers.SlugRelatedField(
        many=True, slug_field="email", queryset=USER.objects.all()
    )

    # Use human readable names instead of actual values in the status field
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.get_status_display()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "project_type",
            "status",
            "percentage",
            "creator",
            "created_at",
            "collaborators",
            "files",
            "algorithms",
        ]
        read_only_fields = ["created_at", "status", "percentage"]


class ActionSerializer(serializers.ModelSerializer):

    associated_user = serializers.SlugRelatedField(
        read_only=True,
        slug_field="email",
    )
    action_type = serializers.SerializerMethodField()
    action_detail = serializers.CharField(max_length=256)
    created = serializers.DateTimeField()

    def get_action_type(self, obj):
        return obj.get_action_type_display()

    class Meta:
        model = Action
        fields = ["associated_user", "action_type", "action_detail", "created"]
        read_only_fields = ["associated_user", "action_type", "created"]
