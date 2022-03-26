from django.contrib.auth.models import User
from django.db import models
from django_countries.fields import CountryField

PROJECT_STATUS_CHOICES = [("CO", "completed"), ("ON", "ongoing"), ("UP", "file_upload"), ("CA", "cancelled")]

class Project(models.Model):
    collaborators = models.ManyToManyField(User)
    created_at = models.DateTimeField(auto_now_add=True)
    project_type = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    status = models.CharField(choices=PROJECT_STATUS_CHOICES, max_length=2)
    percentage = models.SmallIntegerField(default=0)

    def __str__(self):
        return self.name

class Sample(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=256)
    sample_type = models.CharField(max_length=256)
    sample_file = models.FileField(upload_to='samples/')

    def __str__(self):
        return self.name

class Report(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=256)
    report_type = models.CharField(max_length=256)

    def __str__(self):
        return self.name

class Organization(models.Model):
    associated_users = models.ManyToManyField(User)
    name = models.CharField(max_length=256)
    country = CountryField(blank=True)
    address = models.CharField(blank=True, max_length=256)

    def __str__(self):
        return self.name
