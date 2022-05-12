import os
import mmd_scripting.core.nuthouse01_core as core


def ask_for_image_file() -> str:
    """Ask the user for a image file.

    @return: The image file's absolute path
    """
    core.MY_PRINT_FUNC("Please enter name of an image file:")
    file_path = core.MY_FILEPROMPT_FUNC("Image file", [".png", ".tga", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif"])
    return os.path.normpath(os.path.abspath(file_path))
