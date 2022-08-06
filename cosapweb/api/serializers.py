from django.contrib.auth import authenticate, login, password_validation
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
        model = User
        fields = ['username', 'password', 'password_repeat',
                  'first_name', 'last_name', 'email']
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
        user = User.objects.create(
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email']
        )

        user.set_password(validated_data['password'])
        user.save()

        login(self.context.get('request'), user)

        return user


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
