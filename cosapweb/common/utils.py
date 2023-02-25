from ..celery import celery_app
from django.conf import settings
import os

def run_parse_project_data(path):
    """
    Sends parse project results to cosap worker and retrieve data as dict. 
    """
    parse_project_tast = celery_app.send_task(
            "parse_project_results",
            args=[
                path
            ],
        )
    project_data = celery_app.AsyncResult(parse_project_tast.id).get()

    return project_data

def submit_cosap_job():
    pass

def get_user_dir(user):
    user_path = f"{user.id}_{user.email}"
    return os.path.join(settings.MEDIA_ROOT, user_path)