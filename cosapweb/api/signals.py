import os
from pathlib import PurePosixPath
import shutil
from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_drf_filepond.models import TemporaryUpload, TemporaryUploadChunked
from rest_framework.authtoken.models import Token

from ..common.utils import get_user_dir, create_and_get_user_files_dir
from .models import Action, File, Project, Report


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


@receiver(post_save, sender=File)
def auto_extract_file_extension(sender, instance, created, **kwargs):
    if not created:
        return

    """
    Extracts file extension from file name.
    """
    FILE_EXTENSIONS = {
        "FQ": ["fastq", "fq"],
        "BAM": ["bam"],
        "BED": ["bed", "bed6"],
        "VCF": ["vcf"],
        "TXT": ["txt"],
        "JSON": ["json"],
    }

    if instance.name:
        path = PurePosixPath(instance.name)
        suffixes = path.suffixes

        for file_type, extensions in FILE_EXTENSIONS.items():
            if len(set(extensions).intersection(set(suffixes))) > 0:
                instance.file_type = file_type

        instance.save()


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

    permanent_file_path = os.path.join(create_and_get_user_files_dir(fl.user), f"{fl.id}_{upload_file_name}")
    shutil.move(tu.get_file_path(), permanent_file_path)

    fl.name = upload_file_name
    fl.file = permanent_file_path
    fl.save()
