from django.contrib.auth import authenticate, login, password_validation
from rest_framework import serializers
from django.contrib.auth import get_user_model

from cosapweb.api.models import Affiliation, Project, Sample, Action


USER = get_user_model()

class AffiliationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Affiliation
        fields = ["id", "name", "country", "address"]


class UserSerializer(serializers.ModelSerializer):
    # TODO: A user should be allowed to remove or add a relationship to an org.
    Affiliations = AffiliationSerializer(many=True, read_only=True)

    class Meta:
        model = USER
        fields = ["username", "first_name", "last_name", "email",
                  "last_login", "date_joined", "Affiliations"]
        read_only_fields = ["last_login", "date_joined"]

class LoginSerializer(serializers.Serializer):
    """
    Serializer for user authentication.
    Validator tries to authenticate the user with given credentials.
    """

    username = serializers.CharField(
        label="Username",
        write_only=True,
        required=True
    )
    password = serializers.CharField(
        label="Password",
        style={'input_type': 'password'},
        write_only=True,
        trim_whitespace=False,
        required=True
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        # Try to authenticate the user
        user = authenticate(request=self.context.get('request'),
                            username=username, password=password)
        if user is None:
            # Given credentials are invalid, raise a ValidationError
            raise serializers.ValidationError("Invalid username or password.")

        # We have a valid user, make it accessible from validated_data
        attrs['user'] = user
        return attrs


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        validators=[password_validation.validate_password]
    )
    password_repeat = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = USER
        fields = ['pk','username', 'password', 'password_repeat',
                  'first_name', 'last_name', 'email', 'affiliations']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password_repeat']:
            raise serializers.ValidationError(
                {"password_repeat": "Passwords don't match."})

        return attrs

    def create(self, validated_data):
        user = USER.objects.create(
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email']
        )

        user.set_password(validated_data['password'])
        user.save()

        login(self.context.get('request'), user)

        return user


class SampleSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        read_only=True,
        slug_field='email',
    )

    class Meta:
        model = Sample
        fields = ["id", "project", "user", "name",
                  "sample_type", "sample_file", "uploaded_at"]
        read_only_fields = ["uploaded_at"]

    def validate(self, attrs):
        # Users can add samples only to projects they have access to
        user = self.context.get("request").user
        project = attrs["project"]
        if (project.creator != user
                and project not in Project.objects.filter(collaborators=user)):
            raise serializers.ValidationError(
                {"project": "You don't have access to this project!"})

        return attrs


class ProjectSerializer(serializers.ModelSerializer):
    creator = serializers.SlugRelatedField(
        slug_field='email',
        read_only=True
    )
    collaborators = serializers.SlugRelatedField(
        many=True,
        slug_field='email',
        queryset=USER.objects.all()
    )

    # Use human readable names instead of actual values in the status field
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.get_status_display()

    class Meta:
        model = Project
        fields = ["id", "name", "project_type", "status", "percentage",
                  "creator", "created_at", "collaborators", "samples"]
        read_only_fields = ["created_at", "status", "percentage"]

class ActionSerializer(serializers.ModelSerializer):
    
    associated_user = serializers.SlugRelatedField(
        read_only=True,
        slug_field='email',
    )
    action_type = serializers.SerializerMethodField()
    action_detail = serializers.CharField(max_length=256)
    created = serializers.DateTimeField()

    def get_action_type(self, obj):
        return obj.get_action_type_display()

    class Meta:
        model = Action
        fields = ['associated_user', 'action_type', 'action_detail', 'created']
        read_only_fields = ["associated_user","action_type","created"]


