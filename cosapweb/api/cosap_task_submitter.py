import os

from ..celery import celery_app
from ..common.utils import get_user_dir, match_read_pairs
from .models import Project, ProjectFile


def submit_cosap_dna_job(project: Project):

    """
    Takes a Project object and submits a COSAP DNA pipeline job to Celery.
    """

    project_file_obj = ProjectFile.objects.get(project=project)
    normal_files = project_file_obj.files.filter(sample_type="normal")
    tumor_files = project_file_obj.files.filter(sample_type="tumor")
    bed_file = project_file_obj.files.filter(file_type="bed")

    normal_pairs = match_read_pairs([file.name for file in normal_files])
    tumor_pairs = match_read_pairs([file.name for file in tumor_files])

    mappers = project.algorithms["aligner"]
    variant_callers = project.algorithms["variantCaller"]
    annotators = project.algorithms["variantAnnotator"]
    bam_qc = "qualimap"
    workdir = os.path.join(get_user_dir(project.user), project.name)
    project_type = "somatic" if project.project_type == "SM" else "germline"

    # Print args
    print(
        f"project type: {project_type}, workdir: {workdir}, normal pairs: {normal_pairs}, tumor pairs: {tumor_pairs}, bed file: {bed_file}, mappers: {mappers}, variant callers: {variant_callers}, bam qc: {bam_qc}, annotators: {annotators}"
    )

    # cosap_dna_task = celery_app.send_task(
    #     "cosap_dna_pipeline_task",
    #     args=[
    #         project_type,
    #         workdir,
    #         normal_pairs,
    #         tumor_pairs,
    #         bed_file,
    #         mappers,
    #         variant_callers,
    #         bam_qc,
    #         annotators,
    #     ],
    # )
    return #celery_app.AsyncResult(cosap_dna_task.id)
