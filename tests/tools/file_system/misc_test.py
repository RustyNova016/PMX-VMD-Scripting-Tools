import unittest

from mmd_scripting.core.tools.file_system.misc import get_absolute_path_of_parent_directory, get_filename_of_path

test_path = "C:\\Users\\omega\\Documents\\MMD v9.32\\UserFile\\Model\\Elsword\\[Eve]\\[Code - Antithese]\\[Code - Antithese] Edit\\Remy.pmx"

class MiscTests(unittest.TestCase):
    def test_get_absolute_path_of_parent_directory(self):

        self.assertEqual(get_absolute_path_of_parent_directory(test_path), "C:\\Users\\omega\\Documents\\MMD v9.32\\UserFile\\Model\\Elsword\\[Eve]\\[Code - Antithese]\\[Code - Antithese] Edit")  # add assertion here

    def test_get_filename_of_path(self):
        self.assertEqual(get_filename_of_path(test_path), "Remy.pmx")  # add assertion here


if __name__ == '__main__':
    unittest.main()
