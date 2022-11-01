from django.conf import settings
from django.apps import apps
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.auth.hashers import make_password
from django.db import models
from django_countries.fields import CountryField
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

PROJECT_STATUS_CHOICES = [
    ("CO", "completed"), ("ON", "ongoing"), ("UP", "file_upload"), ("CA", "cancelled")]

ACTION_TYPES = [
    ("PC", "project_creation"), ("FU", "file_upload"), ("RC", "report_creation"),("SI", "sample_inspection")
]

class CustomUserManager(UserManager):
    def create_user(self, username=None, email=None, password=None, **extra_fields):
        return super(CustomUserManager, self).create_user(username, email, password, **extra_fields)

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        return super(CustomUserManager, self).create_superuser(username, email, password, **extra_fields)

    def _create_user(self, username, email, password, **extra_fields):
        email = self.normalize_email(email)
        GlobalUserModel = apps.get_model(self.model._meta.app_label, self.model._meta.object_name)
        username = GlobalUserModel.normalize_username(username)
        user = self.model(username=username, email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user


class CustomUser(AbstractUser):
    email = models.EmailField(('email address'), unique=True) # changes email to unique and blank to false
    username = models.CharField(max_length=50, null=True)
    
    objects = CustomUserManager()

    REQUIRED_FIELDS = [] 
    USERNAME_FIELD = 'email'

    
USER = get_user_model()


class Project(models.Model):
    creator = models.ForeignKey(USER, null=True, on_delete=models.SET_NULL)
    collaborators = models.ManyToManyField(USER, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    project_type = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    status = models.CharField(choices=PROJECT_STATUS_CHOICES, max_length=2)
    percentage = models.SmallIntegerField(default=0)

    def __str__(self):
        return self.name


class Sample(models.Model):
    user = models.ForeignKey(USER, null=True, on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='samples')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=256)
    sample_type = models.CharField(max_length=256)
    sample_file = models.FileField(upload_to='sample_files/')

    def __str__(self):
        return self.name


class Report(models.Model):
    user = models.ForeignKey(USER, null=True, on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=256)
    report_type = models.CharField(max_length=256)

    def __str__(self):
        return self.name


class Affiliation(models.Model):
    associated_users = models.ManyToManyField(
        USER, related_name='affiliations')
    name = models.CharField(max_length=256)
    country = CountryField(blank=True)
    address = models.CharField(blank=True, max_length=256)

    def __str__(self):
        return self.name


class Action(models.Model):
    associated_user = models.ForeignKey(
        USER, blank=True, null=True, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(choices=ACTION_TYPES, max_length=2)
    action_detail = models.CharField(max_length=256)
    created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.action_type}_{self.action_detail}"
    
    class Meta:
        ordering = ['created']
    
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)