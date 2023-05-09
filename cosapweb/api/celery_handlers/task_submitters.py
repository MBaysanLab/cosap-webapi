import os

from ...celery import celery_app
from ...common.utils import get_user_dir, match_read_pairs, wait_file_update_complete
from ..models import Project, ProjectFile


def submit_cosap_dna_job(project_id: int):

    """
    Takes a Project object and submits a COSAP DNA pipeline job to Celery.
    """

    project = Project.objects.get(id=project_id)
    project_file_obj = ProjectFile.objects.get(project=project)

    normal_files = project_file_obj.files.filter(sample_type="NORMAL")
    tumor_files = project_file_obj.files.filter(sample_type="TUMOR")
    bed_file = (
        list(project_file_obj.files.filter(file_type="bed"))[0]
        if project_file_obj.files.filter(file_type="bed")
        else None
    )

    normal_pairs = match_read_pairs([file for file in normal_files])[0]
    tumor_pairs = match_read_pairs([file for file in tumor_files])

    mappers = project.algorithms["aligner"]
    variant_callers = project.algorithms["variantCaller"]
    annotators = project.algorithms["variantAnnotator"]
    bam_qc = "qualimap"
    workdir = os.path.join(get_user_dir(project.user), f"{project.id}_{project.name}")
    project_type = "somatic" if project.project_type == "SM" else "germline"

    for file in normal_files:
        wait_file_update_complete(file.file.path)
    for file in tumor_files:
        wait_file_update_complete(file.file.path)

    if bed_file:
        for file in bed_file:
            wait_file_update_complete(file.file.path)

    cosap_dna_task = celery_app.send_task(
        "cosap_dna_pipeline_task",
        kwargs={
            "analysis_type": project_type,
            "workdir": workdir,
            "normal_sample": normal_pairs,
            "tumor_samples": tumor_pairs,
            "bed_file": bed_file,
            "mappers": mappers,
            "variant_callers": variant_callers,
            "tumor_sample_name": "TUMOR",
            "normal_sample_name": "NORMAL",
            "bam_qc": bam_qc,
            "annotation": annotators,
        },
    )
    return cosap_dna_task.id


def submit_cosap_parse_project_data_task(path):
    """
    Sends parse project results to cosap worker and retrieve data as dict.
    """
    parse_project_task = celery_app.send_task(
        "parse_project_results",
        args=[path],
    )
    project_data = celery_app.AsyncResult(parse_project_task.id).get()

    return project_data
