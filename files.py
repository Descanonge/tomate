"""Data files management.

VarGroup:
Stores what variable are in what directory.

Files:
Stores existing variables groups.
"""


from glob import glob


class VarGroup():
    """An ensemble of variables.

    Stored in the same files, in the same directory

    variables: list of strings
    directory: list of directories
    """

    def __init__(self, variables, directory, ncname):
        self.variables = variables
        self.directory = directory
        self.ncname = ncname    # unused

        self.files = self._get_files()

    def _check_ncname(self, vi):
        """Check ncname is consistent with vi."""
        for i, var in enumerate(self.variables):
            if self.ncname[i] != vi.ncname[var]:
                return False
        return True

    def _get_files(self):
        """Get list of files."""
        files = glob(self.directory + '*.nc')
        files.sort()
        return files


class Files():
    """Stores info on how files are arrange on disk.

    , and what variables they hold

    variables: list of groups of variables present in
    the same directory.
    directories: list of directories where files are found
    ncname: corresponding name in netcdf files
    """

    def __init__(self, variables, directories, ncname):
        mess = "Not as much directories as variables groups"
        assert (len(variables) == len(directories)
                and len(variables) == len(ncname)), mess

        self.n = len(variables)

        self.varGroups = []
        for i in range(self.n):
            self.varGroups.append(VarGroup(variables[i],
                                           directories[i],
                                           ncname[i]))

        self.indices = self.get_indices()

    def get_indices(self):
        """Return dictionnary of which group is each variable."""
        groups = self.get_variables()
        indices = {}
        for i in range(self.n):
            for var in groups[i]:
                if var in indices:
                    raise ValueError("variable appearing more than once")
                indices.update({var: i})
        return indices

    def get_var_group(self, var):
        """Return varGroup index containing var."""
        return self.varGroups[self.indices[var]]

    def get_variables(self):
        """Return list of variables in each variable group."""
        variables = [vg.variables for vg in self.varGroups]
        return variables

    def get_directories(self):
        """Return list of directory of each variable group."""
        directories = [vg.directory for vg in self.varGroups]
        return directories

    def _check_ncname(self, vi):
        """Check if ncname is consistent with vi."""
        res = [vg._check_ncname(vi) for vg in self.varGroups]
        return all(res)
