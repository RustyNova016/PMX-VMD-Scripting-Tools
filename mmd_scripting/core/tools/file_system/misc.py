import os


def get_absolute_path_of_parent_directory(path: str) -> str:
    """
    Get the absolute path of the parent directory of the given path.
    """
    return os.path.dirname(os.path.abspath(path))


def get_filename_of_path(path: str) -> str:
    """
    Get the filename of the given path.
    """
    return os.path.basename(path)
