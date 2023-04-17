from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Action, Affiliation, CustomUser, File, Project, Report, Variant

admin.site.register(CustomUser, UserAdmin)
admin.site.register(Affiliation)
admin.site.register(Project)
admin.site.register(File)
admin.site.register(Report)
admin.site.register(Action)
admin.site.register(Variant)
