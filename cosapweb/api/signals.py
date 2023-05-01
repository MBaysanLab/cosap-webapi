import os

from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_drf_filepond.api import store_upload
from django_drf_filepond.models import TemporaryUploadChunked, TemporaryUpload
from rest_framework.authtoken.models import Token

from ..common.utils import run_parse_project_data, submit_cosap_dna_job
from .models import Action, File, Project, Report, ProjectFile
from ..common.utils import get_user_dir


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

@receiver(post_delete, sender=TemporaryUploadChunked)
def save_tmp_upload(sender, instance, **kwargs):
    """
    Saves temporary upload to the file system.
    """
    tmp_id = instance.upload_id

    tu = TemporaryUpload.objects.get(upload_id=tmp_id)
    upload_file_name = tu.upload_name

    fl = File.objects.get(uuid=tmp_id)
    user_dir = get_user_dir(fl.user)
    
    permanent_file_path = os.rename(tu.get_file_path(), os.path.join(user_dir, "files", f"{fl.id}_upload_file_name"))
    fl.name = upload_file_name
    fl.file = permanent_file_path
    fl.save()


# @receiver(post_save, sender=Project)
# def submit_celery_cosap_job(sender, instance, **kwargs):
#     normal_sample = File.objects.filter(project=instance, sample_type="normal")
#     tumor_samples = list(File.objects.filter(project=instance, sample_type="tumor"))
#     mappers = P
#     submit_cosap_dna_job(
#         analysis_type=instance.project_type,
#         normal_sample=instance.normal_sample,
#     )
