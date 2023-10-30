from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django_drf_filepond.models import TemporaryUpload

from .models import (SNV, Action, Affiliation, CustomUser, File, Project,
                     ProjectFiles, ProjectSNVs, ProjectSummary, ProjectTask,
                     Report)

admin.site.register(CustomUser, UserAdmin)
admin.site.register(Affiliation)
admin.site.register(Project)
admin.site.register(File)
admin.site.register(Report)
admin.site.register(Action)
admin.site.register(SNV)
admin.site.register(ProjectSNVs)
admin.site.register(ProjectFiles)
admin.site.register(ProjectTask)
admin.site.register(ProjectSummary)
