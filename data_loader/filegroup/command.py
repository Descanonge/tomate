"""Command for loading data."""


class Command():
    """Information for loading slices of data."""

    def __init__(self):
        self.filename = ""
        self.var_list = ""

        self.n_keys = 0
        self.keys_in = []
        self.keys_slice = []

    def __iter__(self):
        """Iter on keys."""
        return zip(self.keys_in, self.keys_slice)

    def enum(self):
        """Enum on keys."""
        return zip(range(self.n_keys), self.keys_in, self.keys_slice)

    def add_key(self, key_in, key_slice):
        """Add key."""

        self.n_keys += 1
        self.keys_in.append(key_in)
        self.keys_slice.append(key_slice)

    def set_key(self, key_in, key_slice, i=0):
        """Fix key."""
        self.keys_in[i].update(key_in)
        self.keys_slice[i].update(key_slice)

    def add_keys(self, keys_in, keys_slice):
        """Add keys."""
        for i in range(len(keys_in)):
            self.add_key(keys_in[i], keys_slice[i])


def merge_cmd_per_file(commands):
    """Merge commands that correspond to the same file."""

    commands_merged = [commands[0]]
    i = 0
    for cmd in commands[1:]:
        cmd_merged = commands_merged[i]
        if cmd.filename == cmd_merged.filename:
            cmd_merged.add_keys(cmd.keys_in, cmd.keys_slice)
        else:
            commands_merged.append(cmd)
            i += 1

    return commands_merged
