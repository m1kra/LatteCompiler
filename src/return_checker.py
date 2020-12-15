from errors import * # noqa
from runtime import * # noqa

from antlr4gen.LatteParser import LatteParser
from antlr4gen.LatteVisitor import LatteVisitor


class ReturnAbilityChecker(LatteVisitor):
    """
    Validates return statements
    (each branching in each function should have one).
    """
    def __init__(self):
        self.ok = False

    def visitFunDef(self, ctx: LatteParser.FunDefContext):
        function_type = ctx.type_().getText()
        if function_type != VOID: # noqa
            self.ok = False
            self.visitChildren(ctx)
            if not self.ok:
                raise UnreachableReturnError(ctx) # noqa

    def visitRet(self, ctx: LatteParser.RetContext):
        self.ok = True

    def visitVRet(self, ctx: LatteParser.VRetContext):
        self.ok = True

    def visitCond(self, ctx: LatteParser.CondContext):
        if ctx.expr().expr_value:
            self.visit(ctx.stmt())

    def visitCondElse(self, ctx: LatteParser.CondElseContext):
        if self.ok:
            return
        cond = ctx.expr().expr_value
        if cond is True:
            self.visit(ctx.stmt(0))
        elif cond is False:
            self.visit(ctx.stmt(1))
        else:
            self.visit(ctx.stmt(0))
            if not self.ok:
                return
            self.ok = False
            self.visit(ctx.stmt(1))

    def visitWhile(self, ctx: LatteParser.WhileContext):
        if ctx.expr().expr_value:
            self.visit(ctx.stmt())
