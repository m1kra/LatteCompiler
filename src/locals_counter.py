from errors import * # noqa
from runtime import * # noqa


from antlr4gen.LatteParser import LatteParser
from antlr4gen.LatteVisitor import LatteVisitor


class LocalsCounter(LatteVisitor):
    """
    Counts local variables for any functian (assuming reusing).
    Later used by VariableAllocator.
    """
    def __init__(self):
        self.count = 0
        self.max = 0

    def visitFunDef(self, ctx: LatteParser.FunDefContext):
        self.count = 0
        self.max = 0
        self.visitChildren(ctx)
        to_ad = 1
        if isinstance(ctx.parentCtx, LatteParser.TopFunDefContext):
            to_ad = 0
        ctx.locals_count = self.max + to_ad

    def visitArg(self, ctx: LatteParser.ArgContext):
        self.count += len(ctx.ID())

    def visitBlock(self, ctx: LatteParser.BlockStmtContext):
        count = self.count
        self.visitChildren(ctx)
        if self.count > self.max:
            self.max = self.count
        self.count = count

    def visitDecl(self, ctx: LatteParser.DeclContext):
        self.visitChildren(ctx)

    def visitDef(self, ctx: LatteParser.DefContext):
        self.count += 1

    def visitDefAss(self, ctx: LatteParser.DefAssContext):
        self.count += 1

    def visitEAddOp(self, ctx: LatteParser.EAddOpContext):
        self.visitChildren(ctx)
        self.count += 1

    def visitEMulOp(self, ctx: LatteParser.EMulOpContext):
        self.visitChildren(ctx)
        self.count += 1

    def visitERelOp(self, ctx: LatteParser.ERelOpContext):
        self.visitChildren(ctx)
        self.count += 1

    def visitAttrAss(self, ctx: LatteParser.AttrAssContext):
        self.visitChildren(ctx)
        self.count += 1
