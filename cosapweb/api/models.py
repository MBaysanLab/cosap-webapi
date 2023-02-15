import os

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_countries.fields import CountryField
from rest_framework.authtoken.models import Token


class CustomUserManager(UserManager):
    def create_user(self, username=None, email=None, password=None, **extra_fields):
        return super(CustomUserManager, self).create_user(
            username, email, password, **extra_fields
        )

    def create_superuser(
        self, username=None, email=None, password=None, **extra_fields
    ):
        return super(CustomUserManager, self).create_superuser(
            username, email, password, **extra_fields
        )

    def _create_user(self, username, email, password, **extra_fields):
        email = self.normalize_email(email)
        GlobalUserModel = apps.get_model(
            self.model._meta.app_label, self.model._meta.object_name
        )
        username = GlobalUserModel.normalize_username(username)
        user = self.model(username=username, email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user


class CustomUser(AbstractUser):
    email = models.EmailField(
        ("email address"), unique=True
    )  # changes email to unique and blank to false
    username = models.CharField(max_length=50, null=True)

    objects = CustomUserManager()

    REQUIRED_FIELDS = []
    USERNAME_FIELD = "email"


USER = get_user_model()


class Project(models.Model):

    SOMATIC = "SM"
    GERMLINE = "GM"
    PROJECT_TYPE_CHOICES = [(SOMATIC, "somatic"), (GERMLINE, "germline")]

    COMPLETED = "CO"
    IN_PROGRESS = "IP"
    CANCELLED = "CANCELLED"
    PROJECT_STATUS_CHOICES = [
        (COMPLETED, "completed"),
        (IN_PROGRESS, "in_progress"),
        (CANCELLED, "cancelled"),
    ]

    user = models.ForeignKey(USER, null=True, on_delete=models.SET_NULL)
    collaborators = models.ManyToManyField(USER, related_name="projects")
    created_at = models.DateTimeField(auto_now_add=True)
    project_type = models.CharField(choices=PROJECT_TYPE_CHOICES, max_length=256)
    name = models.CharField(max_length=256)
    status = models.CharField(choices=PROJECT_STATUS_CHOICES, max_length=256)
    progress = models.SmallIntegerField(default=0)
    algorithms = models.JSONField(default=dict)

    def __str__(self):
        return self.name


def user_directory_path(instance, filename):
    return f"{instance.user.id}_{instance.user.email}/{instance.project.id}_{instance.project.name}/{filename}"


class File(models.Model):

    FASTQ = "FQ"
    BAM = "BAM"
    BED = "BED"
    VCF = "VCF"
    TEXT = "TXT"
    JSON = "JSON"
    FILE_TYPES = [
        (FASTQ, "fastq"),
        (BAM, "bam"),
        (BED, "bed"),
        (VCF, "vcf"),
        (TEXT, "txt"),
        (JSON, "json"),
    ]

    TUMOR = "TM"
    NORMAL = "NM"
    SAMPLE_TYPES = [(TUMOR, "tumor"), (NORMAL, "normal")]

    user = models.ForeignKey(USER, null=True, on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="files")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=256)
    file_type = models.CharField(choices=FILE_TYPES, max_length=256)
    sample_type = models.CharField(choices=SAMPLE_TYPES, max_length=256)
    file = models.FileField(upload_to=user_directory_path)

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
    associated_users = models.ManyToManyField(USER, related_name="affiliations")
    name = models.CharField(max_length=256)
    country = CountryField(blank=True)
    address = models.CharField(blank=True, max_length=256)

    def __str__(self):
        return self.name


class Action(models.Model):

    PROJECT_CREATION = "PC"
    FILE_UPLOAD = "FU"
    REPORT_CREATION = "RC"
    ACTION_TYPES = [
        (PROJECT_CREATION, "project_creation"),
        (FILE_UPLOAD, "file_upload"),
        (REPORT_CREATION, "report_creation"),
    ]

    associated_user = models.ForeignKey(
        USER, blank=True, null=True, on_delete=models.CASCADE, related_name="actions"
    )
    action_type = models.CharField(choices=ACTION_TYPES, max_length=2)
    action_detail = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.action_type}_{self.action_detail}"

    class Meta:
        ordering = ["created_at"]


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Creates auth token when a user is created.
    """
    if created:
        Token.objects.create(user=instance)


@receiver(post_delete, sender=File)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `File` object is deleted.
    """
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)


@receiver(post_save, sender=Project)
@receiver(post_save, sender=File)
@receiver(post_save, sender=Report)
def auto_create_action(sender, instance, **kwargs):

    if isinstance(instance, Project):
        action_type = "PC"
    elif isinstance(instance, File):
        action_type = "FU"
    elif isinstance(instance, Report):
        action_type = "RC"

    action_obj = Action.objects.create(
        associated_user=instance.user,
        action_type=action_type,
        action_detail=instance.__str__(),
    )
    action_obj.save()
