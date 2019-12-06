"""Command for loading data."""


class Command():
    """Information for loading slices of data."""

    def __init__(self):
        self.filename = ""
        self.var_list = []

        self.n_keys = 0
        self.keys_in = []
        self.keys_slice = []

    def __iter__(self):
        """Iter on keys."""
        return zip(self.keys_in, self.keys_slice)

    def __str__(self):
        s = []
        s.append("file: %s" % self.filename)
        if self.var_list:
            s.append("variables: " + str(self.var_list))
        if self.keys_in:
            s.append("keys in: " + str(self.keys_in))
        if self.keys_slice:
            s.append("keys slice: " + str(self.keys_slice))
        return "\n".join(s)

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
        for i, key_in in enumerate(keys_in):
            self.add_key(key_in, keys_slice[i])

    def remove_key(self, idx):
        """Remove keys."""
        self.keys_in.pop(idx)
        self.keys_slice.pop(idx)
        self.n_keys -= 1

    def merge_keys(self):
        """Merge successive keys."""
        coords = [z for z in self.keys_in[0].keys() if isinstance(self.keys_in[0][z], list)
                  and isinstance(self.keys_slice[0][z], list)]

        for name in coords:
            coords_ = [z for z in coords if z != name]

            i = 1
            while i < self.n_keys:
                key_in_old = self.keys_in[i-1]
                key_sl_old = self.keys_slice[i-1]
                key_in = self.keys_in[i]
                key_sl = self.keys_slice[i]

                # Check keys for other coords are identical
                for name_ in coords_:
                    if key_in[name_] != key_in_old[name_]:
                        continue
                    if key_sl[name_] != key_in_old[name_]:
                        continue

                iscont, k_in, k_sl = iscontiguous(key_in[name], key_in_old[name],
                                                  key_sl[name], key_sl_old[name])
                if iscont:
                    key_in[name] = k_in
                    key_sl[name] = k_sl
                    self.set_key(key_in, key_sl, i-1)
                    self.remove_key(i)
                    i -= 1
                else:
                    i += 1


def iscontiguous(k_in, k_in_old, k_sl, k_sl_old):
    """Check if two keys are contiguous.

    Only work if keys are list, and the new key to append is of length one.
    """
    if len(k_in) == 1 and len(k_sl) == 1:
        if (k_in[0] == k_in_old[-1] + 1) and (k_sl[0] == k_sl_old[-1] + 1):
            k_in_new = k_in_old + k_in
            k_sl_new = k_sl_old + k_sl
            return True, k_in_new, k_sl_new

    return False, None, None


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
