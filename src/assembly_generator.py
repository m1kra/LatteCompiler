import copy

from runtime import *
from latte_state import WithLatteState
from assembly_writer import AssemblyWriter
from variable_allocator import VariableAllocator

from antlr4gen.LatteParser import LatteParser
from antlr4gen.LatteVisitor import LatteVisitor


class AssemblyGenerator(LatteVisitor, WithLatteState):
    """
    Main backend class - generates x68 assembly code.
    """
    def __init__(self, strings: list, writer: AssemblyWriter):
        super().__init__()
        self.strings = strings
        self.labels = {}
        self.writer = writer

        self.ret_label = None
        self.locals = None
        self.locals_count = 0

        self.empty_string_label = ''
        self.empty_string_used = 0

    def newl(self):
        return self.writer.newl()

    def add(self, inst: str, cmt: str = ''):
        self.writer.add(inst, cmt)

    def putl(self, label):
        self.writer.putl(label)

    def prepare_data_section(self):
        for cls in self.classes:
            self.labels[cls] = self.newl()
        for string in self.strings:
            self.labels[string] = self.newl()
        self.empty_string_label = self.newl()

    def init_function(self, name, locals_count):
        self.putl(name)
        signature = self.methods[self.current_object][self.current_fun]
        self.add('push EBP')
        self.add('mov EBP, ESP')
        self.add(f'sub dword ESP, {4 * locals_count}')
        offset = 0
        self.locals = VariableAllocator(locals_count)
        if self.current_object:
            self.add('mov dword EAX, [EBP + 8]', 'copy self')
            self.add('mov dword [EBP + -4], EAX', 'copy self')
            self.locals['self'] = -4
            offset = 4
        for i, (name, var_type) in enumerate(signature[1]):
            self.locals[name] = - 4 * i - 4 - offset
            self.add(
                f'mov dword EAX, [EBP + {8 + 4 * i + offset}]',
                f'copy arg {name}'
            )
            self.add(
                f'mov dword [EBP + -{4 + 4 * i + offset}], EAX',
                f'copy arg {name}'
            )

    def visitProgram(self, ctx: LatteParser.ProgramContext):
        self.prepare_data_section()
        self.visitChildren(ctx)
        self.writer.gen_text_intro()
        self.writer.gen_data_section(
            self.strings, self.classes, self.labels, self.vtables,
            self.empty_string_used, self.empty_string_label
        )

    def visitTopFunDef(self, ctx: LatteParser.TopFunDefContext):
        self.current_object = None
        return super().visitTopFunDef(ctx)

    def visitBaseClassDef(self, ctx: LatteParser.BaseClassDefContext):
        self.current_object = ctx.ID().getText()
        return super().visitBaseClassDef(ctx)

    def visitExtClassDef(self, ctx: LatteParser.ExtClassDefContext):
        self.current_object = ctx.ID(0).getText()
        return super().visitExtClassDef(ctx)

    def visitFunDef(self, ctx: LatteParser.FunDefContext):
        name = ctx.ID().getText()
        self.current_fun = name
        name = f'{self.current_object}__{name}' if self.current_object else name
        self.ret_label = self.newl()
        self.init_function(name, ctx.locals_count)
        self.visitChildren(ctx)
        self.putl(self.ret_label)
        self.add('leave')
        self.add('ret')
        self.current_fun = None

    def visitBlock(self, ctx: LatteParser.BlockContext):
        old_locals = copy.deepcopy(self.locals)
        self.visitChildren(ctx)
        self.locals = old_locals

    def visitDecl(self, ctx: LatteParser.DeclContext):
        self.current_type = ctx.type_().getText()
        return super().visitDecl(ctx)

    def visitDef(self, ctx: LatteParser.DefContext):
        name = ctx.ID().getText()
        self.locals.new(name)
        self.init_var(name, 'default')

    def visitDefAss(self, ctx: LatteParser.DefAssContext):
        self.visit(ctx.expr())
        name = ctx.ID().getText()
        self.locals.new(name)
        self.init_var(name, 'EAX')

    def init_var(self, name, mode):
        val = 0
        if mode == 'default':
            if self.current_type in {INT, BOOL}:
                val = 0
            elif self.current_type == STRING:
                val = self.empty_string_label
                self.empty_string_used = True
            else:
                self.add('mov dword EAX, 0', f'init {name} to 0')
        if mode == 'EAX':
            val = 'EAX'
        self.add(
            f'mov dword [EBP + {self.locals[name]}], {val}',
            f'init {name} to expr in eax'
        )

    def visitAss(self, ctx: LatteParser.AssContext):
        self.visit(ctx.expr())
        name = ctx.ID().getText()
        if name in self.locals:
            self.add(
                f'mov dword [EBP + {self.locals[name]}], EAX',
                f'line {ctx.start.line}: {name}='
            )
        else:
            # the only possibility is that we are in a method
            # and we are writing to an attribute
            self.add('mov ECX, EAX', f'line {ctx.start.line}: self.{name}=')
            self.add('mov EAX, [EBP + -4]', 'as above')
            attrs = list(self.attrs[self.current_object].keys())
            index = attrs.index(ctx.ID().getText())
            self.add(f'mov [EAX + {4 + 4 * index}], ECX', 'as above')

    def visitAttrAss(self, ctx: LatteParser.AttrAssContext):
        self.visit(ctx.expr(0))
        var = self.locals.new()
        self.add(
            f'mov [EBP + {var}], EAX',
            f'at line {ctx.start.line} ({ctx.start.line}=...): '
            f'proceed to calculate expression'
        )
        self.visit(ctx.expr(1))
        self.add(
            'mov ECX, EAX',
            f'at line {ctx.start.line} ({ctx.ID().getText()}=): copy result'
        )
        self.add(f'mov EAX, [EBP + {var}]', 'then get object ptr')
        self.locals.free(var)
        attrs = list(self.attrs[ctx.expr(0).expr_type].keys())
        index = attrs.index(ctx.ID().getText())
        self.add(f'mov [EAX + {4 + 4 * index}], ECX', 'and save with offset')

    def visitArrayAss(self, ctx: LatteParser.ArrayAssContext):
        return super().visitArrayAss(ctx)

    def visit_inc_dec(self, op, name, cls):
        if name in self.locals:
            self.add(
                f'{op} dword [EBP + {self.locals[name]}]',
                f'{name}{op}'
            )
        else:
            attrs = list(self.attrs[cls].keys())
            index = attrs.index(name)
            self.add(
                f'{op} dword [EAX + {4 + 4 * index}]',
                f'self.{name}{op}'
            )

    def visitIncr(self, ctx: LatteParser.IncrContext):
        self.visit_inc_dec('inc', ctx.ID().getText(), self.current_object)

    def visitDecr(self, ctx: LatteParser.DecrContext):
        self.visit_inc_dec('dec', ctx.ID().getText(), self.current_object)

    def visitAttrIncr(self, ctx: LatteParser.AttrIncrContext):
        self.visit(ctx.expr())
        self.visit_inc_dec('inc', ctx.ID().getText(), ctx.expr().expr_type)

    def visitAttrDecr(self, ctx: LatteParser.AttrDecrContext):
        self.visit(ctx.expr())
        self.visit_inc_dec('dec', ctx.ID().getText(), ctx.expr().expr_type)

    def visitRet(self, ctx: LatteParser.RetContext):
        self.visit(ctx.expr())
        self.add(
            f'jmp {self.ret_label}',
            f'goto return at line {ctx.start.line}'
        )

    def visitVRet(self, ctx: LatteParser.VRetContext):
        self.add(
            f'jmp {self.ret_label}',
            f'goto return at line {ctx.start.line}'
        )

    def visitCond(self, ctx: LatteParser.CondContext):
        self.visit(ctx.expr())
        finish_label = self.newl()
        self.add('cmp EAX, 1', f'if at line {ctx.start.line}')
        self.add(f'jne {finish_label}', 'if ne omit if\'s body')
        self.visit(ctx.stmt())
        self.putl(finish_label)

    def visitCondElse(self, ctx: LatteParser.CondElseContext):
        self.visit(ctx.expr())
        finish_label = self.newl()
        if_label = self.newl()
        self.add('cmp EAX, 0', f'if else at line {ctx.start.line}')
        self.add(f'jne {if_label}', f'if ne goto if part')
        self.visit(ctx.stmt(1))
        self.add(
            f'jmp {finish_label}',
            f'finish "if" from line {ctx.start.line}'
        )
        self.putl(if_label)
        self.visit(ctx.stmt(0))
        self.putl(finish_label)

    def visitWhile(self, ctx: LatteParser.WhileContext):
        checkl, bodyl, finishl = self.newl(), self.newl(), self.newl()
        self.putl(checkl)
        self.visit(ctx.expr())
        self.add('cmp EAX, 0', f'while from line {ctx.start.line}')
        self.add(f'jne {bodyl}', 'if ne jump to while\' body')
        self.add(f'jmp {finishl}', 'else jump to finish label')
        self.putl(bodyl)
        self.visit(ctx.stmt())
        self.add(
            f'jmp {checkl}',
            f'return to condition in while from line {ctx.start.line}'
        )
        self.putl(finishl)

    def visitForEach(self, ctx: LatteParser.ForEachContext):
        return super().visitForEach(ctx)

    def visitEId(self, ctx: LatteParser.EIdContext):
        name = ctx.ID().getText()
        if name in self.locals:
            self.add(
                f'mov EAX, [EBP + {self.locals[name]}]',
                f'get value of var "{name}" at line {ctx.start.line}'
            )
        else:
            attrs = list(self.attrs[self.current_object].keys())
            index = attrs.index(ctx.ID().getText())
            self.add(
                'mov EAX, [EBP + -4]',
                f'<- get self from self.{name}= in line {ctx.start.line}'
            )
            self.add(f'mov EAX, [EAX + {4 + 4 * index}]', 'get attr')

    def visit_vcall(self, name, args, methods):
        self.add('mov dword EAX, [EBP + -4]', 'vcall: get self')
        self.add('push dword EAX', 'vcall: put self on stack (as first arg)')
        self.add(f'mov dword EAX, [EAX]', 'vcall: get vtable of self')
        offset = 4 * methods.index(name)
        self.add(f'mov dword EAX, [EAX + {offset}]', 'vcall: get method')
        self.add('call EAX', 'vcall: make call')
        self.add(f'add ESP, {4 * 4 * len(args)}', 'vcall: clean stack')

    def visitEFunCall(self, ctx: LatteParser.EFunCallContext):
        name = ctx.ID().getText()
        args = [expr for expr in ctx.expr()]
        for arg in args[::-1]:
            self.visit(arg)
            self.add(
                "push dword EAX",
                f'push arg from call "{name}" at line {ctx.start.line}'
            )
        if self.current_object:
            methods = [mthd[1] for mthd in self.vtables[self.current_object]]
            if name in methods:
                self.visit_vcall(name, args, methods)
                return
        self.add(f'call {name}', f'call "{name}", line {ctx.start.line}')
        self.add(f'add ESP, {4 * len(args)}', 'and clean stack')

    def visitEMthdCall(self, ctx: LatteParser.EMthdCallContext):
        exprs = list(ctx.expr())
        name = ctx.ID().getText()
        for expr in exprs[::-1]:
            self.visit(expr)
            self.add(
                'push EAX',
                f'push arg from call "{name}" at line {ctx.start.line}'
            )
        self.add(
            'mov dword EAX, [EAX]',
            f'vcall {name} at line {ctx.start.line}: load vtable'
        )
        methods = [p[1] for p in self.vtables[exprs[0].expr_type]]
        offset = 4 * methods.index(ctx.ID().getText())
        self.add(f'mov dword EAX, [EAX + {offset}]', 'vcall: load method')
        self.add('call EAX', 'vcall: make call')
        self.add(f'add dword ESP, {4 * len(exprs)}', 'clean stack')

    def visitERelOp(self, ctx: LatteParser.ERelOpContext):
        self.visit(ctx.expr(0))
        op = ctx.relOp().getText()
        var = self.locals.new()
        self.add(f'mov [EBP + {var}], EAX', f'{op} op at line {ctx.start.line}')
        self.visit(ctx.expr(1))
        self.add(f'mov ECX, [EBP + {var}]', f'{op} op at line {ctx.start.line}')
        self.locals.free(var)
        self.add('cmp ECX, EAX', f'{op} op at line {ctx.start.line}')
        inst = {
            '<': 'setl',
            '<=': 'setle',
            '>=': 'setge',
            '>': 'setg',
            '==': 'sete',
            '!=': 'setne'
        }[op]
        self.add(f'{inst} AL', f'{op} op at line {ctx.start.line}')
        self.add(f'and dword EAX, 1', f'{op} op at line {ctx.start.line}')

    def visitETrue(self, ctx: LatteParser.ETrueContext):
        self.add('mov dword EAX, 1', f'true at line {ctx.start.line}')

    def visitEFalse(self, ctx: LatteParser.EFalseContext):
        self.add('xor EAX, EAX', f'false at line {ctx.start.line}')

    def visitEInt(self, ctx: LatteParser.EIntContext):
        self.add(
            f'mov dword EAX, {ctx.getText()}',
            f'const. {ctx.getText()} at line {ctx.start.line}'
        )

    def visitEStr(self, ctx: LatteParser.EStrContext):
        self.add(
            f'mov dword EAX, {self.labels[ctx.getText()]}',
            f'line {ctx.start.line}, const. str: {ctx.getText()}'
        )

    def visitECastNull(self, ctx: LatteParser.ECastNullContext):
        self.add('mov dword EAX, 0', f'cast null at line {ctx.start.line}')

    def visitENewArr(self, ctx: LatteParser.ENewArrContext):
        return super().visitENewArr(ctx)

    def visit_and_or(self, ctx, op):
        finishl = self.newl()
        self.visit(ctx.expr(0))
        self.add('cmp EAX, 0', f'boolean op')
        self.add(f'{op} {finishl}', f'with lazy evaluation')
        self.visit(ctx.expr(1))
        self.putl(finishl)

    def visitEOr(self, ctx: LatteParser.EOrContext):
        self.visit_and_or(ctx, 'jne')

    def visitEAnd(self, ctx: LatteParser.EAndContext):
        self.visit_and_or(ctx, 'je')

    def visitEUnOp(self, ctx: LatteParser.EUnOpContext):
        self.visit(ctx.expr())
        if isinstance(ctx.unOp(), LatteParser.MinusContext):
            self.add('neg dword EAX', f'- at line {ctx.start.line}')
        else:
            self.add('xor dword EAX, 1', f'! at line {ctx.start.line}')

    def visitEArrAcc(self, ctx: LatteParser.EArrAccContext):
        return super().visitEArrAcc(ctx)

    def visitENewObj(self, ctx: LatteParser.ENewObjContext):
        cls = ctx.type_().getText()
        if cls not in self.classes:
            # well, new int? that's cheating
            return
        num_fields = len(list(self.attrs[cls].keys()))
        self.add(
            f'push dword {4 * (1 + num_fields)}',
            f'new {cls} at line {ctx.start.line} - push obj size'
        )
        self.add(f'call _malloc', 'and allocate memory')
        self.add(f'add ESP, 4', 'clean after call')
        if self.vtables[cls]:
            # if it is a struct, there is no vtable
            self.add(
                f'mov dword [EAX], {self.labels[cls]}',
                f'and set first addres to {cls}\'s vtable'
            )

    def visitEMulOp(self, ctx: LatteParser.EMulOpContext):
        self.visit(ctx.expr(0))
        var = self.locals.new()
        self.add(
            f'mov [EBP + {var}], EAX',
            f'left subexpression of mulOp from line {ctx.start.line}'
        )
        self.visit(ctx.expr(1))
        self.add('mov ECX, EAX', f'prepare mulOp, line {ctx.start.line}')
        self.add(f'mov EAX, [EBP + {var}]', f'as above')
        self.locals.free(var)
        code = {
            '*': 'mul ECX',
            '/': 'cdq;div ECX',
            '%': 'cdq;div ECX;mov EAX, ECX'
        }[self.visit(ctx.mulOp())]

        for instr in code.split(';'):
            self.add(instr, f'do mulOp from line {ctx.start.line}')

    def visitEAddOp(self, ctx: LatteParser.EAddOpContext):
        self.visit(ctx.expr(0))
        var = self.locals.new()
        self.add(
            f'mov [EBP + {var}], EAX',
            f'left subexpression of addOp from line {ctx.start.line}'
        )
        self.visit(ctx.expr(1))
        self.add(
            f'mov ECX, [EBP + {var}]',
            f'prepare addOp, line {ctx.start.line}'
        )
        self.locals.free(var)
        op = self.visit(ctx.addOp())
        if op == '+':
            if ctx.expr_type == STRING:
                self.add('push EAX', f'concat strings in line {ctx.start.line}')
                self.add('push ECX', f'as above')
                self.add('call _concat', f'as above')
                self.add('add dword ESP, 8', 'as above')
            else:
                self.add('add EAX, ECX', f'add, line {ctx.start.line}')
        else:
            self.add('sub ECX, EAX', f'sub, line {ctx.start.line}')
            self.add('mov EAX, ECX', 'as above')

    def visitEParen(self, ctx: LatteParser.EParenContext):
        self.visitChildren(ctx)

    def visitEAttr(self, ctx: LatteParser.EAttrContext):
        self.visit(ctx.expr())
        attrs = list(self.attrs[ctx.expr().expr_type].keys())
        name = ctx.ID().getText()
        self.add(
            f'mov EAX, [EAX + {4 * attrs.index(name) + 4}]',
            f'getattr with name {name} in line {ctx.start.line}'
        )

    def visitESelf(self, ctx: LatteParser.ESelfContext):
        self.add('mov EAX, [EBP + -4]', 'load self')

    def visitArray(self, ctx: LatteParser.ArrayContext):
        return super().visitArray(ctx)

    # region Operators

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
    # endregion
