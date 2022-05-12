import json
import unittest
import mmd_scripting.core.nuthouse01_io as nuthouse01_io


class ReadJsonFile(unittest.TestCase):
    def testReadTheJsonIntoDict(self):
        json_data = nuthouse01_io.read_jsonfile_to_dict("testJSON.json")
        print(json_data)
        self.assertEqual(json_data, {"test": "test"})

    def testExceptionOnMissingFile(self):
        with self.assertRaises(FileNotFoundError):
            json_data = nuthouse01_io.read_jsonfile_to_dict("testJSON2.json")

    def testExceptionOnInvalidFile(self):
        with self.assertRaises(json.JSONDecodeError):
            json_data = nuthouse01_io.read_jsonfile_to_dict("testInvalidJSON.json")


if __name__ == '__main__':
    unittest.main()
