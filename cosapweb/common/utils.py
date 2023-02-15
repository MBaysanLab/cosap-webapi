from ..celery import celery_app

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

