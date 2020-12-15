from antlr4gen.LatteParser import LatteParser
from antlr4gen.LatteVisitor import LatteVisitor


class TreeOptimizer(LatteVisitor):
    """
    Fronted optimizer which (to some extent) removes dead code.
    """
    def visitCond(self, ctx: LatteParser.CondContext):
        val = ctx.expr().expr_value
        idx = ctx.parentCtx.children.index(ctx)
        if val:
            ctx.parentCtx.children[idx] = ctx.stmt()
        if val is False:
            ctx.parentCtx.children[idx] =\
                LatteParser.EmptyContext(LatteParser, ctx.parentCtx)

    def visitCondElse(self, ctx: LatteParser.CondElseContext):
        cond = ctx.expr().expr_value
        idx = ctx.parentCtx.children.index(ctx)
        if cond is True:
            ctx.parentCtx.children[idx] = ctx.stmt(0)
        elif cond is False:
            ctx.parentCtx.children[idx] = ctx.stmt(1)

    def visitWhile(self, ctx: LatteParser.WhileContext):
        cond = ctx.expr().expr_value
        idx = ctx.parentCtx.children.index(ctx)
        if cond is False:
            ctx.parentCtx.children[idx] =\
                LatteParser.EmptyContext(LatteParser, ctx.parentCtx)

    def visitDefAss(self, ctx: LatteParser.DefAssContext):
        expr = ctx.expr()
        if expr.expr_value is not None:
            idx = ctx.children.index(expr)
            ctx.children[idx] = self.make_node(expr.expr_value, ctx)

    def visitAss(self, ctx: LatteParser.AssContext):
        expr = ctx.children[2]
        if expr.expr_value is not None:
            ctx.children[2] = self.make_node(expr.expr_value, ctx)

    def visitEFunCall(self, ctx: LatteParser.EFunCallContext):
        for i, expr in enumerate(ctx.expr()):
            if expr.expr_value is not None:
                # add 1 for ID and 1 for '(' - terminal node
                ctx.children[2 + 2 * i] = self.make_node(expr.expr_value, ctx)

    def visitEMthdCall(self, ctx: LatteParser.EMthdCallContext):
        args = [e for e in ctx.expr()][1:]
        for i, arg in enumerate(args):
            if arg.expr_value is not None:
                # add 4 for expr, '.' and '('
                ctx.children[4 + 2 * i] = self.make_node(arg.expr_value, ctx)

    @staticmethod
    def make_node(expr_value, parent):
        node_type = {
            str: LatteParser.EStrContext,
            int: LatteParser.EIntContext,
            True: LatteParser.ETrueContext,
            False: LatteParser.EFalseContext
        }[expr_value if isinstance(expr_value, bool) else type(expr_value)]
        node = node_type(LatteParser, parent)
        node.getText = lambda: str(expr_value)
        return node
