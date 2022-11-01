from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Affiliation, Project, Sample, Report, CustomUser, Action

admin.site.register(CustomUser, UserAdmin)
admin.site.register(Affiliation)
admin.site.register(Project)
admin.site.register(Sample)
admin.site.register(Report)
admin.site.register(Action)