class FileRecord:
    """A struct to bundle all the relevant info about a file that is on disk or used by PMX"""

    def __init__(self, name, exists):
        # the "current name" name this file uses in the PMX: relative to startpath and separator-normalized
        # (because these are made after normalize_texture_paths() is called).
        # or, if it does not exist on disk, whatever name shows up in the PMX entry
        self.name = name
        # true if this is a real file that exists on disk
        self.exists = exists
        # dict of all PMX that reference this file at least once:
        # keys are strings which are filepath relative to startpath and separator-normalized
        # values are index it appears at, saves searching time
        self.used_pmx = dict()
        # set of all ways this file is used within PMXes
        self.usage = set()
        # total number of times this file is used... not required for the script, just interesting stats
        self.numused = 0
        # the name this file will be renamed to
        self.newname = None

    def __str__(self) -> str:
        p = "'%s': used as %s, %d times among %d files" % (
            self.name, self.usage, self.numused, len(self.used_pmx))
        return p
