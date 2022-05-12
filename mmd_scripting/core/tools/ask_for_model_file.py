import os
import mmd_scripting.core.nuthouse01_core as core


def ask_for_model_file() -> str:
    """
    Ask the user for a model file.

    @return: The model file's absolute path
    """
    core.MY_PRINT_FUNC("Please enter name of a PMX model file:")
    file_path = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
    return os.path.normpath(os.path.abspath(file_path))
