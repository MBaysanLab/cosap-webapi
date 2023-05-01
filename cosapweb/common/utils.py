import os

from django.conf import settings

from ..celery import celery_app

def match_read_pairs(file_list: list) -> list[tuple]:
    """
        Matches read 1 and read 2 from paired end sequencing.
    """

    file_list.sort()
    read_1 = []
    read_2 = []

    for file in file_list:
        if "_R1_" in file:
            read_1.append(file)
        elif "_R2_" in file:
            read_2.append(file)

    if len(read_1) != len(read_2):
        raise ValueError("Some pairs are missing.")
    
    return list(zip(read_1, read_2))

def run_parse_project_data(path):
    """
    Sends parse project results to cosap worker and retrieve data as dict.
    """
    parse_project_task = celery_app.send_task(
        "parse_project_results",
        args=[path],
    )
    project_data = celery_app.AsyncResult(parse_project_task.id).get()

    return project_data


def submit_cosap_dna_job(
    analysis_type,
    workdir,
    normal_sample,
    tumor_sample,
    bed_file,
    mappers,
    variant_callers,
    normal_sample_name,
    tumor_sample_name,
    bam_qc,
    annotation,
):

    cosap_dna_task = celery_app.send_task(
        "cosap_dna_pipeline_task",
        args=[
            analysis_type,
            workdir,
            normal_sample,
            tumor_sample,
            bed_file,
            mappers,
            variant_callers,
            normal_sample_name,
            tumor_sample_name,
            bam_qc,
            annotation,
        ],
    )
    return celery_app.AsyncResult(cosap_dna_task.id)


def get_user_dir(user):
    user_path = f"{user.id}_{user.email}"
    return os.path.join(settings.MEDIA_ROOT, user_path)
