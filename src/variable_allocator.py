

class VariableAllocator:
    """
    Keeps mapping: variable name -> offset.
    Reuses 4 * `locals_count` memory when allocating variables.
    """
    def __init__(self, locals_count: int):
        self._free = {- 4 * k for k in range(1, locals_count + 1)}
        self.names = {}

    def __setitem__(self, key, value):
        if key in self.names:
            self._free.add(self.names[key])
        self.names[key] = value
        if value in self._free:
            self._free.remove(value)

    def __getitem__(self, key):
        return self.names[key]

    def __delitem__(self, key):
        self._free.add(self.names[key])
        del self.names[key]

    def __contains__(self, item):
        return item in self.names

    def new(self, name=None):
        val = self._free.pop()
        if name:
            if name in self.names:
                self._free.add(self.names[name])
            self.names[name] = val
        return val

    def free(self, val):
        self._free.add(val)
