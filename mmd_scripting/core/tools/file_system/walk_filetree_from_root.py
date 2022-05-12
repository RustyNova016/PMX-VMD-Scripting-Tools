import os
from typing import List


def walk_filetree_from_root(starting_path: str) -> List[str]:
    absolute_all_exist_files = []
    # os.walk: returns (path to the folder i'm in),(list of folders in this folder),(list of files in this folder)
    for where, subfolders, files in os.walk(starting_path):
        absolute_all_exist_files += [os.path.join(where, f) for f in files]
    relative_all_exist_files = [os.path.relpath(f, starting_path) for f in absolute_all_exist_files]
    return relative_all_exist_files
