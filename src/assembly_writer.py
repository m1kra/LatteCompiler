

class AssemblyWriter:
    """ 
    Formatting of assembly and comments.
    Builds constant/static sections and remembers labels.
    """
    def __init__(self):
        self._i = 0
        self.instructions = []
        self.comments = []

    def newl(self):
        self._i += 1
        return f'l{self._i}'

    def add(self, inst: str, comment: str = ''):
        self.instructions.append(f'    {inst}')
        self.comments.append(comment)

    def putl(self, label):
        self.instructions.append(f'{label}:  ')
        self.comments.append('')

    def gen_data_section(
            self, strings, classes, labels, vtables, is_empty, empty_label
    ):
        sec = ['segment .data']
        for string in strings:
            sec.append(
                f'    {labels[string]}:  dd  `{string}`, 0'.replace('"', '')
            )
        if is_empty:
            sec.append(f'    {empty_label}:  dd  ``, 0')
        for cls in classes:
            vtable = [f'{cls}__{m}' for cls, m in vtables[cls]]
            if vtable:
                sec.append(
                    f'    {labels[cls]}:  dd  {", ".join(vtable)}      '
                    f'; vtable of class {cls}'
                )
        if len(sec) == 1:
            return
        self.instructions = sec + self.instructions
        self.comments = len(sec) * [''] + self.comments

    def gen_text_intro(self):
        sec = [
            'segment .text',
            '  global main',
            '  extern printInt',
            '  extern printString',
            '  extern readInt',
            '  extern readString',
            '  extern error',
            '  extern _concat',
            '  extern _str_equal',
            '  extern _malloc'
        ]
        self.instructions = sec + self.instructions
        self.comments = [''] * 10 + self.comments

    def remove(self, to_remove):
        to_remove.sort(key=lambda x: -x)
        for i in to_remove:
            del self.instructions[i]
            del self.comments[i]

    def get_code(self):
        idx = self.instructions.index('segment .text')
        m = max(map(len, self.instructions[idx:])) + 4
        res = []
        for ins, cmt in zip(self.instructions, self.comments):
            length = max(m - len(ins), 4)
            res.append(ins + length * ' ' + '; ' + cmt)
        return '\n'.join(res)
