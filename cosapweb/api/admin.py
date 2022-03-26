from django.contrib import admin

from .models import Organization, Project, Sample, Report

admin.site.register(Organization)
admin.site.register(Project)
admin.site.register(Sample)
admin.site.register(Report)