from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from django.conf import settings
from django.db.models.signals import post_delete, post_save
from .models import File, Project, Report, Action
import os

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

@receiver(post_save, sender=Project)
def submit_cosap_job(sender, instance, **kwargs):
    pass