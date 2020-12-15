from copy import deepcopy
from functools import wraps

from runtime import * # noqa
from errors import * # noqa
from latte_state import WithLatteState

from antlr4gen.LatteParser import LatteParser
from antlr4gen.LatteVisitor import LatteVisitor


def register_type(type_checking_method):
    """
    Adds expression type to AST node.
    Used for expressions validaation.
    """
    @wraps(type_checking_method)
    def new_method(obj, ctx):
        ret_type = type_checking_method(obj, ctx)
        ctx.expr_type = ret_type
        return ret_type
    return new_method


class ErrorChecker(LatteVisitor, WithLatteState):
    """
    A frontend class which mostly type-checks the code,
    returning (hopefully) meaningful errors.
    """
    def __init__(self):
        super().__init__()
        self.globals = {}
        self.locals = {}

    def visitProgram(self, ctx: LatteParser.ProgramContext):
        if 'main' not in self.methods[self.OBJECT]:
            raise MissingMainFunctionError(
                ctx,
                'No main function found.'
            )

        return super().visitProgram(ctx)

    def visitTopFunDef(self, ctx: LatteParser.TopFunDefContext):
        self.current_object = self.OBJECT
        return super().visitTopFunDef(ctx)

    def visitBaseClassDef(self, ctx: LatteParser.BaseClassDefContext):
        name = ctx.ID().getText()
        self.current_object = name
        return super().visitBaseClassDef(ctx)

    def visitExtClassDef(self, ctx: LatteParser.ExtClassDefContext):
        name, sup = ctx.ID(0).getText(), ctx.ID(1).getText()
        if sup not in self.classes.keys():
            raise UndeclaredClassError(
                ctx,
                f'There is no class with name "{sup}".'
            )
        self.current_object = name
        return super().visitExtClassDef(ctx)

    def visitFieldDef(self, ctx: LatteParser.FieldDefContext):
        field_type = ctx.type_().getText()
        if not self._correct_var_type(field_type):
            raise UnknownTypeError(
                ctx.type_(),
                f'The type "{field_type}" cannot be recognized.'
            )
        super().visitFieldDef(ctx)

    def visitFunDef(self, ctx: LatteParser.FunDefContext):
        name = ctx.ID().getText()
        ret_type, args = self.methods[self.current_object][name]
        arg_types = [arg[1] for arg in args]
        if not self._correct_ret_type(ret_type):
            raise UnknownReturnTypeError(
                ctx,
                f'The type "{ret_type}" cannot be recognized.'
            )
        if not all(self._correct_var_type(t) for t in arg_types):
            raise UnknownArgumentTypeError(
                ctx,
                f'Function "{name}" has an argument with unrecognized type.'
            )
        if self.current_object:
            cls = self.classes[self.current_object]
            while cls:
                # bad override checks
                if name in self.methods[cls]:
                    sup_ret_type, sup_args = self.methods[cls][name]
                    sup_arg_types = [arg[1] for arg in sup_args]
                    if ret_type != sup_ret_type:
                        raise BadOverrideError(
                            ctx,
                            f'The return type "{ret_type}" of method "{name}" '
                            f'doesnt match the return type "{sup_ret_type}" '
                            f'in the superclass "{cls}".'
                        )
                    if arg_types != sup_arg_types:
                        raise BadOverrideError(
                            ctx,
                            f'The argument types of method "{name}" dont match '
                            f'the argument types in the superclass "{cls}".'
                        )
                cls = self.classes[cls]
        self.current_fun = name
        self.locals = {k: v for k, v in args}
        self.visitChildren(ctx)

    # # # STATEMENTS # # #

    def visitBlock(self, ctx: LatteParser.BlockContext):
        old_globals, old_locals = deepcopy(self.globals), deepcopy(self.locals)
        self.globals.update(self.locals)
        self.locals = {}
        self.visitChildren(ctx)
        self.globals, self.locals = old_globals, old_locals

    def visitDecl(self, ctx: LatteParser.DeclContext):
        # TODO: make this working for arrays
        var_type = ctx.type_().getText()
        if not self._correct_var_type(var_type):
            raise UnknownTypeError(
                ctx,
                f'The type "{var_type}" cannot be recognized.'
            )
        self.current_type = var_type
        super().visitDecl(ctx)

    def visitDef(self, ctx: LatteParser.DefContext):
        name = ctx.ID().getText()
        if name in self.locals:
            raise VariableRedeclarationError(
                ctx,
                f'The variable "{name}" is already declared in current scope.'
            )
        self.locals[name] = self.current_type

    def visitDefAss(self, ctx: LatteParser.DefAssContext):
        name = ctx.ID().getText()
        if name in self.locals:
            raise VariableRedeclarationError(
                ctx,
                f'The variable "{name}" is already declared in current scope.'
            )
        expr_type = self.visit(ctx.expr())
        if not self.is_subtype(expr_type, self.current_type):
            raise TypeMismatchError(
                ctx,
                f'The RHS type "{expr_type}" is '
                f'incompatible with "{self.current_type}".'
            )
        self.locals[name] = self.current_type

    def visitAss(self, ctx: LatteParser.AssContext):
        name = ctx.ID().getText()
        var_type = self._var_type(name, ctx)
        expr_type = self.visit(ctx.expr())
        if not self.is_subtype(expr_type, var_type):
            raise TypeMismatchError(
                ctx,
                f'The RHS type "{expr_type}" is '
                f'incompatible with variable\'s type "{var_type}".'
            )

    def visitAttrAss(self, ctx: LatteParser.AttrAssContext):
        attr_name = ctx.ID().getText()
        lhs = self.visit(ctx.expr(0))
        attr_type = self._attr_type(lhs, attr_name, ctx)
        rhs = self.visit(ctx.expr(1))
        if not self.is_subtype(rhs, attr_type):
            raise TypeMismatchError(
                ctx,
                f'The RHS type "{rhs}" is incompatible with '
                f'attribute "{attr_name}" type "{attr_type}".'
            )

    def _visit_inc_dec(self, ctx):
        name = ctx.ID().getText()
        var_type = self._var_type(name, ctx)
        if var_type != INT:
            raise UnsupportedOperandError(
                ctx,
                'Operators ++ / -- are only supported for INT type.'
            )

    def visitIncr(self, ctx: LatteParser.IncrContext):
        self._visit_inc_dec(ctx)

    def visitDecr(self, ctx: LatteParser.DecrContext):
        self._visit_inc_dec(ctx)

    def _visit_attr_inc_dec(self, ctx):
        cls = self.visit(ctx.expr())
        name = ctx.ID().getText()
        if name not in self.attrs[cls]:
            raise MissingAttributeError(
                ctx,
                f'There is no attribute {name} in class {cls}.'
            )
        if self.attrs[cls][name] != INT:
            raise UnsupportedOperandError(
                ctx,
                '++ / -- are only supported for INT type.'
            )

    def visitAttrIncr(self, ctx: LatteParser.AttrIncrContext):
        self._visit_attr_inc_dec(ctx)

    def visitAttrDecr(self, ctx: LatteParser.AttrDecrContext):
        self._visit_attr_inc_dec(ctx)

    def visitRet(self, ctx: LatteParser.RetContext):
        should_ret = self.methods[self.current_object][self.current_fun][0]
        if self.visit(ctx.expr()) != should_ret:
            raise InvalidReturnTypeError(
                ctx,
                f'The return type should be '
                f'{should_ret}, not {ctx.expr().expr_type}.'
            )

    def visitVRet(self, ctx: LatteParser.VRetContext):
        should_ret = self.methods[self.current_object][self.current_fun][0]
        if should_ret != VOID:
            raise InvalidReturnTypeError(
                ctx,
                f'The return type should be {should_ret}, not VOID.'
            )

    def visitCond(self, ctx: LatteParser.CondContext):
        if self.visit(ctx.expr()) != BOOL:
            raise BadConditionError(ctx, 'Only boolean conditions supported.')
        self.visit(ctx.stmt())

    def visitCondElse(self, ctx: LatteParser.CondElseContext):
        if self.visit(ctx.expr()) != BOOL:
            raise BadConditionError(ctx, 'Only boolean conditions supported.')
        self.visit(ctx.stmt(0))
        self.visit(ctx.stmt(1))

    def visitWhile(self, ctx: LatteParser.WhileContext):
        if self.visit(ctx.expr()) != BOOL:
            raise BadConditionError(ctx, 'Only boolean conditions supported.')
        self.visit(ctx.stmt())

    def visitForEach(self, ctx: LatteParser.ForEachContext):
        raise ArraysNotImplemented(ctx)

    def visitArrayAss(self, ctx: LatteParser.ArrayAssContext):
        raise ArraysNotImplemented(ctx)

    def visitENewArr(self, ctx: LatteParser.ENewArrContext):
        raise ArraysNotImplemented(ctx)

    def visitEArrAcc(self, ctx: LatteParser.EArrAccContext):
        raise ArraysNotImplemented(ctx)

    @register_type
    def visitETrue(self, ctx: LatteParser.ETrueContext):
        return BOOL

    @register_type
    def visitEFalse(self, ctx: LatteParser.EFalseContext):
        return BOOL

    @register_type
    def visitEInt(self, ctx: LatteParser.EIntContext):
        return INT

    @register_type
    def visitEStr(self, ctx: LatteParser.EStrContext):
        return STRING

    @register_type
    def visitESelf(self, ctx: LatteParser.ESelfContext):
        if not self.current_object:
            raise InvalidReferenceError(
                ctx,
                '"self" can only be used inside method, not function.'
            )
        return self.current_object

    @register_type
    def visitEId(self, ctx: LatteParser.EIdContext):
        name = ctx.ID().getText()
        return self._var_type(name, ctx)

    @register_type
    def visitEFunCall(self, ctx: LatteParser.EFunCallContext):
        name = ctx.ID().getText()
        arg_types = [self.visit(arg) for arg in ctx.expr()]
        return self._fun_call_type(self.current_object, name, arg_types, ctx)

    @register_type
    def visitEMthdCall(self, ctx: LatteParser.EMthdCallContext):
        types = [self.visit(e) for e in ctx.expr()]
        cls, arg_types = types[0], types[1:]
        return self._fun_call_type(cls, ctx.ID().getText(), arg_types, ctx)

    @register_type
    def visitEUnOp(self, ctx: LatteParser.EUnOpContext):
        exp_type = self.visit(ctx.expr())
        if isinstance(ctx.unOp(), LatteParser.MinusContext):
            if exp_type == INT:
                return INT
        if isinstance(ctx.unOp(), LatteParser.NegContext):
            if exp_type == BOOL:
                return BOOL
        raise UnsupportedOperandError(
            ctx,
            '"-" is only supported for INT, and "!" for BOOL'
        )

    @register_type
    def visitERelOp(self, ctx: LatteParser.ERelOpContext):
        arg1, arg2 = [self.visit(arg) for arg in ctx.expr()]
        if arg1 == arg2 == INT:
            return BOOL
        if type(ctx.relOp()) in {LatteParser.NeqContext, LatteParser.EqContext}:
            if self.is_subtype(arg1, arg2):
                return BOOL
        raise UnsupportedOperandError(
            ctx,
            '<, >, <=, >= are only supported for INT\n== and != '
            'work for compatible classes (i.e. one inherits from other)'
        )

    @register_type
    def visitECastNull(self, ctx: LatteParser.ECastNullContext):
        type_ = ctx.type_().getText()
        if type_ not in self.classes:
            raise UndeclaredClassError(
                ctx,
                f'there is no class with name {type_}'
            )
        return type_

    def _visit_or_and(self, ctx):
        arg1, arg2 = [self.visit(arg) for arg in ctx.expr()]
        if arg1 == arg2 == BOOL:
            return BOOL
        raise UnsupportedOperandError(
            ctx,
            '&& and || only work for BOOL arguments'
        )

    @register_type
    def visitEOr(self, ctx: LatteParser.EOrContext):
        return self._visit_or_and(ctx)

    @register_type
    def visitEAnd(self, ctx: LatteParser.EAndContext):
        return self._visit_or_and(ctx)

    @register_type
    def visitEMulOp(self, ctx: LatteParser.EMulOpContext):
        arg1, arg2 = [self.visit(arg) for arg in ctx.expr()]
        if arg1 == arg2 == INT:
            return INT
        raise UnsupportedOperandError(
            ctx,
            '/ and * only work for INT variables'
        )

    @register_type
    def visitEAddOp(self, ctx: LatteParser.EAddOpContext):
        arg1, arg2 = [self.visit(arg) for arg in ctx.expr()]
        if arg1 == arg2 == INT:
            return INT
        if arg1 == arg2 == STRING and ctx.addOp().getText() == '+':
            return STRING
        raise UnsupportedOperandError(
            ctx,
            '- only works for INT variables, + only for INT and STR'
        )

    @register_type
    def visitENewObj(self, ctx: LatteParser.ENewObjContext):
        obj_type = ctx.type_().getText()
        if obj_type not in self.classes:
            raise UndeclaredClassError(
                ctx,
                f'Missing declaration of class {obj_type}'
            )
        return obj_type

    @register_type
    def visitEParen(self, ctx: LatteParser.EParenContext):
        return self.visit(ctx.expr())

    @register_type
    def visitEAttr(self, ctx: LatteParser.EAttrContext):
        expr_type = self.visit(ctx.expr())
        if expr_type not in self.classes:
            raise UndeclaredClassError(
                ctx,
                f'Missing declaration of class {expr_type}'
            )
        attr_name = ctx.ID().getText()
        return self._attr_type(expr_type, attr_name, ctx)

    def _correct_var_type(self, type_name: str) -> bool:
        return type_name in GENERIC_TYPES or type_name in self.classes.keys()

    def _correct_ret_type(self, type_name: str) -> bool:
        return type_name == VOID or self._correct_var_type(type_name)

    def _var_type(self, var_name, ctx):
        var_type = self.locals.get(
            var_name,
            self.globals.get(
                var_name,
                self.attrs[self.current_object].get(
                    var_name,
                    None
                )
            )
        )
        if var_type is None:
            raise UndeclaredVariableError(
                ctx,
                f'Missing declaration of variable {var_name}.'
            )
        return var_type

    def _attr_type(self, cls, attr, ctx):
        while cls is not None:
            if attr in self.attrs[cls]:
                return self.attrs[cls][attr]
            cls = self.classes[cls]
        raise MissingAttributeError(
            ctx, f'Missing attribute {attr} in class {cls}'
        )

    def _fun_call_type(self, cls, name, arg_types, ctx):
        while True:
            if name in self.methods[cls]:
                rtype, args = self.methods[cls][name]
                if len(arg_types) != len(args):
                    raise ArgumentMismatchError(
                        ctx,
                        f"Invalid number of arguments. "
                        f"Given {len(arg_types)}, should be {len(args)}."
                    )
                for i, arg in enumerate(args):
                    if not self.is_subtype(arg_types[i], arg[1]):
                        raise ArgumentMismatchError(
                            ctx,
                            f'Invalid argument type: {arg_types[i]} != {arg[1]}'
                        )
                return rtype
            if cls is None:
                raise UndeclaredFunctionError(
                    ctx, f'Missing function declaration of {name}.'
                )
            cls = self.classes[cls]
