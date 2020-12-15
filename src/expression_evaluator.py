from functools import wraps

from antlr4gen.LatteParser import LatteParser
from antlr4gen.LatteVisitor import LatteVisitor


def is_variable(*args):
    """
    True iff an expression arising from `args`
    is not constant and cannot be eliminated.
    """
    return any(arg is None for arg in args)


def register_value(method):
    """
    Adds expression value to AST node.
    Used when evaluating constant expressions/
    """
    @wraps(method)
    def new_method(obj, ctx):
        val = method(obj, ctx)
        ctx.expr_value = val
        return val
    return new_method


class ExpressionEvaluator(LatteVisitor):
    """
    A frontend class which eliminates constant expressions.
    """
    @register_value
    def visitEId(self, ctx: LatteParser.EIdContext):
        return None

    @register_value
    def visitEFunCall(self, ctx: LatteParser.EFunCallContext):
        self.visitChildren(ctx)
        return None

    @register_value
    def visitERelOp(self, ctx: LatteParser.ERelOpContext):
        a1, a2 = self.visit(ctx.expr(0)), self.visit(ctx.expr(1))
        if is_variable(a1, a2):
            return None
        return {
            '<': a1 < a2,
            '<=': a1 <= a2,
            '>': a1 > a2,
            '>=': a1 >= a2,
            '==': a1 == a2,
            '!=': a1 != a2
        }[self.visit(ctx.relOp())]

    @register_value
    def visitETrue(self, ctx: LatteParser.ETrueContext):
        return True

    @register_value
    def visitECastNull(self, ctx: LatteParser.ECastNullContext):
        return None

    def visitENewArr(self, ctx: LatteParser.ENewArrContext):
        return super().visitENewArr(ctx)

    @register_value
    def visitEOr(self, ctx: LatteParser.EOrContext):
        a1, a2 = self.visit(ctx.expr(0)), self.visit(ctx.expr(1))
        return a1 or a2

    @register_value
    def visitEAnd(self, ctx: LatteParser.EAndContext):
        a1, a2 = self.visit(ctx.expr(0)), self.visit(ctx.expr(1))
        return a1 and a2

    @register_value
    def visitEInt(self, ctx: LatteParser.EIntContext):
        return int(ctx.INT().getText())

    @register_value
    def visitEUnOp(self, ctx: LatteParser.EUnOpContext):
        v = self.visit(ctx.expr())
        if is_variable(v):
            return None
        return {
            '-': -v,
            '!': not v
        }[ctx.unOp().getText()]

    @register_value
    def visitEStr(self, ctx: LatteParser.EStrContext):
        return ctx.STR().getText().strip('"')

    @register_value
    def visitEArrAcc(self, ctx: LatteParser.EArrAccContext):
        return None

    @register_value
    def visitENewObj(self, ctx: LatteParser.ENewObjContext):
        return None

    @register_value
    def visitEMulOp(self, ctx: LatteParser.EMulOpContext):
        a1, a2 = self.visit(ctx.expr(0)), self.visit(ctx.expr(1))
        if is_variable(a1, a2):
            return None
        op = ctx.mulOp().getText()
        if op == '*':
            return a1 * a2
        if a2 == 0:
            raise ZeroDivisionError(ctx)
        return {
            '/': a1 / a2,
            '%': a1 % a2
        }[op]

    @register_value
    def visitEAddOp(self, ctx: LatteParser.EAddOpContext):
        a1, a2 = self.visit(ctx.expr(0)), self.visit(ctx.expr(1))
        if is_variable(a2, a1):
            return None
        if ctx.addOp().getText() == '+':
            return a1 + a2
        else:
            return a1 - a2

    @register_value
    def visitEParen(self, ctx: LatteParser.EParenContext):
        return self.visit(ctx.expr())

    @register_value
    def visitEFalse(self, ctx: LatteParser.EFalseContext):
        return False

    @register_value
    def visitEMthdCall(self, ctx: LatteParser.EMthdCallContext):
        self.visitChildren(ctx)
        return None

    @register_value
    def visitESelf(self, ctx: LatteParser.ESelfContext):
        return None

    @register_value
    def visitEAttr(self, ctx: LatteParser.EAttrContext):
        return None

    def visitMinus(self, ctx: LatteParser.MinusContext):
        return '-'

    def visitNeg(self, ctx: LatteParser.NegContext):
        return '!'

    def visitAdd(self, ctx: LatteParser.AddContext):
        return '+'

    def visitSub(self, ctx: LatteParser.SubContext):
        return '-'

    def visitMul(self, ctx: LatteParser.MulContext):
        return '*'

    def visitDiv(self, ctx: LatteParser.DivContext):
        return '/'

    def visitMod(self, ctx: LatteParser.ModContext):
        return '%'

    def visitLt(self, ctx: LatteParser.LtContext):
        return '<'

    def visitLe(self, ctx: LatteParser.LeContext):
        return '<='

    def visitGt(self, ctx: LatteParser.GtContext):
        return '>'

    def visitGe(self, ctx: LatteParser.GeContext):
        return '>='

    def visitEq(self, ctx: LatteParser.EqContext):
        return '=='

    def visitNeq(self, ctx: LatteParser.NeqContext):
        return '!='
