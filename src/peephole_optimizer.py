from assembly_writer import AssemblyWriter


class PeepholeOptimizer:
    """
    Class for peephole optimization, interacts with AssemblyWriter.
    """
    def __init__(self, writer: AssemblyWriter):
        self.writer = writer

    def iter_instructions(self, k: int):
        t = len(self.writer.instructions) - k
        if t > 0:
            for i in range(t):
                chunk = []
                for j in range(k):
                    chunk.append(
                        self.sanitize(self.writer.instructions[i + j])
                    )
                yield i, chunk

    @staticmethod
    def sanitize(instruction):
        if ':' in instruction:
            return instruction
        instruction = instruction.replace('dword ', '').strip()
        if ',' in instruction:
            x, c = instruction.split(',')
            y = x.find(' ')
            return x[:y].strip(), x[y:].strip(), c.strip()
        return instruction.split(' ')

    def optimize(self):
        self.mov__eax_c__mem_eax()
        self.mov_ab_xd_ba()
        self.mov_ab_ac()
        self.mov_ab_ab()
        self.jmp_lbl_lbl()
        self.mov_ab_ba()

    def mov_ab_ba(self):
        to_remove = []
        for i, (ab, ba) in self.iter_instructions(2):
            if len(ab) == len(ba) == 3:
                if ab[0] == ba[0] == 'mov':
                    if ab[1] == ba[2] and ab[2] == ba[1]:
                        to_remove.append(i + 1)
        self.writer.remove(to_remove)

    def mov_ab_xd_ba(self):
        to_remove = []
        for i, (ab, xd, ba) in self.iter_instructions(3):
            if ':' in xd:
                continue
            if len(ab) == len(ba) == 3:
                if ab[0] == ba[0] == 'mov':
                    if ab[1] == ba[2] and ab[2] == ba[1]:
                        if ab[1] not in xd or (
                                len(xd) == 3 and xd[1] != ab[1]
                        ):
                            to_remove.append(i + 2)
        self.writer.remove(to_remove)

    def mov_ab_ab(self):
        to_remove = []
        for i, (a, b) in self.iter_instructions(2):
            if len(a) == len(b) == 3:
                if a[0] == b[0] == 'mov':
                    if a[2] == b[2] and a[1] == b[1] and a[1] not in b[2]:
                        to_remove.append(i + 1)
        self.writer.remove(to_remove)

    def mov_ab_ac(self):
        to_remove = []
        for i, (ab, ac) in self.iter_instructions(2):
            if len(ab) == len(ac) == 3:
                if ab[0] == ac[0] == 'mov':
                    if ab[1] == ac[1] and ab[1] not in ac[2]:
                        to_remove.append(i + 1)
        self.writer.remove(to_remove)

    def mov__eax_c__mem_eax(self):
        to_remove = []
        for i, (a, b) in self.iter_instructions(2):
            if len(a) == len(b) == 3 and a[0] == b[0] == 'mov':
                if a[1] == 'EAX' and b[2] == 'EAX' and '[' not in a[2]:
                    self.writer.instructions[i] =\
                        f'    mov dword {b[1]}, {a[2]}'
                    to_remove.append(i + 1)
        self.writer.remove(to_remove)

    def jmp_lbl_lbl(self):
        to_remove = []
        for i, (jmp, lbl) in self.iter_instructions(2):
            if 'jmp' in jmp and ':' in lbl:
                if jmp[1] == lbl.split(':')[0]:
                    to_remove.append(i)
        self.writer.remove(to_remove)
