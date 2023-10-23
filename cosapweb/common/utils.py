import os
from datetime import datetime
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

def get_user_files_dir(user):
    user_path = get_user_dir(user)
    user_files_path = os.path.join(user_path, "files")
    os.makedirs(user_files_path, exist_ok=True)
    return user_files_path

def get_project_dir(project):
    return os.path.join(get_user_dir(project.user), f"{project.id}_{project.name}")

def convert_file_relative_path_to_absolute_path(file_path: str) -> str:
    """
    Converts relative path to absolute path.
    """
    return os.path.join(settings.MEDIA_ROOT, file_path)

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

def get_relative_to_media_root(path):
    return os.path.relpath(path, settings.MEDIA_ROOT)

def create_chonky_filemap(dir, project_name):

    """
    Walks directory and returns Chonky file map and root folder id.
    """
    def get_stats(path):
        st = os.stat(path)
        return {
            'id': f"{st.st_dev}-{st.st_ino}",
            'size': st.st_size,
            'modDate': str(datetime.fromtimestamp(st.st_mtime)),
        }

    def walk(dir_path, root_dir_id, root_folder_name):
        for entry in os.scandir(dir_path):
            full_path = entry.path
            rel_path = get_relative_to_media_root(entry)
            parent_stats = get_stats(dir_path)
            parent_id = f"{parent_stats['id']}"
            stats = get_stats(full_path)
            file_id = f"{stats['id']}"

            if entry.is_dir():
                if file_id not in file_map:
                    file_map[file_id] = {
                        'id': file_id,
                        'name': entry.name,
                        'isDir': True,
                        'childrenIds': [],
                        'path': rel_path,
                    }

                    if file_id != parent_id:
                        file_map[file_id]['parentId'] = parent_id

                if parent_id not in file_map:
                    file_map[parent_id] = {
                        'id': parent_id,
                        'name': root_folder_name if parent_id == root_dir_id else entry.name,
                        'isDir': True,
                        'childrenIds': [file_id],
                        'path': rel_path,
                    }
                else:
                    file_map[parent_id]['childrenIds'].append(file_id)

                yield from walk(full_path, root_dir_id, root_folder_name)

            elif entry.is_file():
                if parent_id not in file_map:
                    file_map[parent_id] = {
                        'id': parent_id,
                        'name': root_folder_name if parent_id == root_dir_id else entry.name,
                        'isDir': True,
                        'childrenIds': [file_id],
                        'path': get_relative_to_media_root(dir_path),
                    }
                else:
                    file_map[parent_id]['childrenIds'].append(file_id)

                file_map[file_id] = {
                    'id': file_id,
                    'name': entry.name,
                    'parentId': parent_id,
                    'size': stats['size'],
                    'modDate': stats['modDate'],
                    'path': rel_path,
                }

                yield full_path

    if not os.path.exists(dir):
        return None

    root_dir = os.path.abspath(dir)
    root_dir_id = f"{os.stat(root_dir).st_dev}-{os.stat(root_dir).st_ino}"
    
    file_map = {}
    for _ in walk(root_dir, root_dir_id, project_name):
        pass

    return {
        'root_folder_id': root_dir_id,
        'file_map': file_map
    }
