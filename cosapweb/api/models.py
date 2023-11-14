import os
import uuid

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django_countries.fields import CountryField


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
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    PROJECT_STATUS_CHOICES = [
        (PENDING, "pending"),
        (COMPLETED, "completed"),
        (IN_PROGRESS, "in_progress"),
        (CANCELLED, "cancelled"),
        (FAILED, "failed"),
    ]

    user = models.ForeignKey(USER, null=True, on_delete=models.SET_NULL)
    collaborators = models.ManyToManyField(USER, related_name="projects", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    project_type = models.CharField(choices=PROJECT_TYPE_CHOICES, max_length=256)
    name = models.CharField(max_length=256)
    status = models.CharField(choices=PROJECT_STATUS_CHOICES, max_length=256)
    progress = models.SmallIntegerField(default=0)
    algorithms = models.JSONField(default=dict)
    is_demo = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.id} - {self.name}"


class ProjectSummary(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    mapped_reads = models.FloatField()
    mean_coverage = models.FloatField()
    number_of_variants = models.IntegerField()
    number_of_significant_variants = models.IntegerField()
    number_of_vus = models.IntegerField()
    msi_score = models.FloatField(null=True, blank=True)
    cnv_count = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.project.name} - summary"


class SNV(models.Model):
    location = models.CharField(max_length=256)
    ref = models.CharField(max_length=256)
    alt = models.CharField(max_length=256)
    function = models.TextField(max_length=256, null=True, blank=True)
    gene_symbol = models.CharField(max_length=256, null=True, blank=True)
    consequence = models.TextField(max_length=256, null=True, blank=True)
    coding_consequece = models.TextField(max_length=256, null=True, blank=True)
    ens_gene = models.CharField(max_length=256, null=True, blank=True)
    feature = models.TextField(max_length=256, null=True, blank=True)
    hgvsc = models.CharField(max_length=256, null=True, blank=True)
    classification = models.CharField(max_length=256, null=True, blank=True)
    gnomad_af = models.FloatField(null=True, blank=True)
    aa_change = models.TextField(max_length=256, null=True, blank=True)
    rs_id = models.CharField(max_length=256, null=True, blank=True)
    sift_score = models.FloatField(null=True, blank=True)
    polyphen_score = models.FloatField(null=True, blank=True)
    interpro_domain = models.TextField(max_length=256, null=True, blank=True)
    clinical_significance = models.TextField(max_length=256, null=True, blank=True)
    cosmic_id = models.CharField(max_length=256, null=True, blank=True)
    clinvar_classification = models.TextField(max_length=256, null=True, blank=True)
    evidence = models.TextField(max_length=256, null=True, blank=True)
    orphanet_info = models.TextField(max_length=256, null=True, blank=True)
    other_info = models.TextField(max_length=256, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.location} - {self.gene_symbol}"


class ProjectSNVs(models.Model):
    project = models.ForeignKey(Project, null=True, on_delete=models.CASCADE)
    snvs = models.ManyToManyField(SNV)

    def __str__(self) -> str:
        return f"{self.project.id}_{self.project.name} - snvs"


class ProjectSNVData(models.Model):
    project = models.ForeignKey(Project, null=True, on_delete=models.CASCADE)
    snv = models.ForeignKey(SNV, null=True, on_delete=models.SET_NULL)
    allele_frequency = models.FloatField(default=0.43)

    def __str__(self) -> str:
        return f"{self.project.id}_{self.project.name} - snv data"


class SV(models.Model):
    pass


class ProjectSV(models.Model):
    pass


class CNV(models.Model):
    pass


class ProjectCNV(models.Model):
    pass


class GeneFusion(models.Model):
    pass


class ProjectGeneFusion(models.Model):
    pass


def user_directory_path(instance, filename):
    return os.path.join(f"{instance.user.id}_{instance.user.email}", "files", filename)


class File(models.Model):

    TUMOR = "TUMOR"
    NORMAL = "NORMAL"
    SAMPLE_TYPES = [(TUMOR, "tumor"), (NORMAL, "normal")]

    user = models.ForeignKey(USER, null=True, on_delete=models.SET_NULL)
    uuid = models.CharField(max_length=256, default=uuid.uuid4, editable=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=256, blank=True, null=True)
    file_type = models.CharField(max_length=64, blank=True, null=True)
    sample_type = models.CharField(
        choices=SAMPLE_TYPES, null=True, blank=True, max_length=256
    )
    file = models.FileField(upload_to=user_directory_path)
    is_demo = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.id}-{self.name}"


class ProjectFiles(models.Model):
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True)
    files = models.ManyToManyField(File)

    def __str__(self):
        return f"{self.project.name}_files"


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
    action_detail = models.CharField(max_length=256, null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.action_type}_{self.action_detail}"

    class Meta:
        ordering = ["created_at"]


class ProjectTask(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    task_id = models.CharField(max_length=256)

    def __str__(self):
        return f"{self.project.name} - task_id:{self.task_id}"
