from antlr4gen.LatteParser import LatteParser
from antlr4gen.LatteVisitor import LatteVisitor


class StringFinder(LatteVisitor):
    """
    Finds and returns all strings in program.
    """
    def __init__(self):
        self._strings = []

    def get_strings(self):
        return self._strings

    def visitEStr(self, ctx: LatteParser.EStrContext):
        self._strings.append(ctx.getText())
