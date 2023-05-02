import os

from django.conf import settings


def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    # len(s1) >= len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = (
                previous_row[j + 1] + 1
            )  # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1  # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

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
    
    pair_list = list(zip(read_1, read_2))

    for pair in pair_list:
        if levenshtein(pair[0], pair[1]) != 1:
            raise ValueError("Some pairs are not matching.")
    
    return pair_list


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

def get_user_dir(user):
    user_path = f"{user.id}_{user.email}"
    return os.path.join(settings.MEDIA_ROOT, user_path)

