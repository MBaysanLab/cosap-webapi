from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django_drf_filepond.models import TemporaryUpload

from .models import (Action, Affiliation, CustomUser, File, Project,
                     ProjectFile, ProjectTask, ProjectVariant, Report, Variant)

admin.site.register(CustomUser, UserAdmin)
admin.site.register(Affiliation)
admin.site.register(Project)
admin.site.register(File)
admin.site.register(Report)
admin.site.register(Action)
admin.site.register(Variant)
admin.site.register(ProjectVariant)
admin.site.register(ProjectFile)
admin.site.register(ProjectTask)
admin.site.register(TemporaryUpload)
