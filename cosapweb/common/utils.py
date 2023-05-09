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
        Takes list of file object returns paths of paired files as list of tuples.
    """
    
    file_obj_names = [(file, file.name) for file in file_list]

    file_obj_names = sorted(file_obj_names, key=lambda x: x[1])
    read_1 = []
    read_2 = []

    for file, file_name in file_obj_names:
        if "_R1_" in file_name:
            read_1.append((file,file_name))
        elif "_R2_" in file_name:
            read_2.append((file, file_name))

    if len(read_1) != len(read_2):
        raise ValueError("Some pairs are missing.")
    
    pair_list = list(zip(read_1, read_2))

    for pair in pair_list:
        if levenshtein(pair[0][1], pair[1][1]) != 1:
            raise ValueError("Some pairs are not matching.")
    
    return [(pair[0][0].file.path, pair[1][0].file.path) for pair in pair_list]

def get_user_dir(user):
    user_path = f"{user.id}_{user.email}"
    return os.path.join(settings.MEDIA_ROOT, user_path)


def wait_file_update_complete(file_path: str, timeout: int = 600) -> bool:
    """
    Waits for file to be updated.
    """
    import time

    start_time = time.time()
    while time.time() - start_time < timeout:
        if time.time() - os.path.getmtime(file_path) > 1:
            return
        time.sleep(0.1)
    raise Exception("File upload not complete")