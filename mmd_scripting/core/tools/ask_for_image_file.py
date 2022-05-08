import mmd_scripting.core.nuthouse01_core as core


def ask_for_model_file() -> str:
    """
    Ask the user for a model file.
    """
    core.MY_PRINT_FUNC("Please enter name of an image file:")
    return core.MY_FILEPROMPT_FUNC("Image file", [".png", ".tga", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif"])
