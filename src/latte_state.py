from collections import OrderedDict

from runtime import * # noqa
from errors import * # noqa

from antlr4gen.LatteParser import LatteParser


class WithLatteState:
    """
    Mixin for classes which make use of "state".
    State consists of two things:
        - general program info: classes, methods / functions, attributes etc.
        - local info: currently visited object / method etc.
    """
    def __init__(self):
        self.OBJECT = None
        self.classes = {}
        self.methods = {
            self.OBJECT: {
                printInt: (VOID, [(None, INT)]),
                printString: (VOID, [(None, STRING)]),
                readInt: (INT, []),
                readString: (STRING, []),
                error: (VOID, [])
            }
        }
        self.attrs = {self.OBJECT: {}}
        self.vtables = {}

        self.current_object = self.OBJECT
        self.current_fun = None
        self.current_type = None

    def get_state(self):
        return self.classes, self.methods, self.attrs, self.vtables

    def set_state(self, classes, methods, attrs, vtables):
        self.classes = classes
        self.methods = methods
        self.attrs = attrs
        self.vtables = vtables

    def is_subtype(self, base: str, sup: str) -> bool:
        if base in GENERIC_TYPES:
            return base == sup
        while base is not None:
            if base == sup:
                return True
            base = self.classes[base]
        return False


class LatteStateLoader(WithLatteState):
    """
    Class which reads state (as above) from raw AST tree. 
    """
    # TODO: move offset calculation here
    def load(self, ctx: LatteParser.ProgramContext):
        """ Main method for reading state."""
        functions = list(
            ctx.getChildren(
                lambda c: isinstance(c, LatteParser.TopFunDefContext)
            )
        )
        classes = list(
            ctx.getChildren(
                lambda c: type(c) in {
                    LatteParser.BaseClassDefContext,
                    LatteParser.ExtClassDefContext
                }
            )
        )
        for cls in classes:
            self._load_type(cls)
            self._preload_fields(cls)
        for fun in functions:
            self._load_function_header(self.OBJECT, fun.funDef())
        for cls in classes:
            self._load_headers(cls)
            self._load_fields(cls)
        self.build_vtables()

    def _load_type(self, ctx):
        name, parent = self._get_cls_and_sup(ctx)
        if name in self.classes.keys():
            raise ClassRedeclarationError(ctx)
        self.classes[name] = parent
        self.methods[name] = {}
        self.attrs[name] = {}

    def _load_fields(self, ctx):
        cls, sup = self._get_cls_and_sup(ctx)
        fields, ancestors = {}, [cls]
        while sup is not None:
            ancestors.append(sup)
            sup = self.classes[sup]
        for anc in ancestors[::-1]:
            fields.update(self.attrs[anc])
        self.attrs[cls] = fields

    def _preload_fields(self, ctx):
        name, _ = self._get_cls_and_sup(ctx)
        fields = list(
            ctx.getChildren(
                lambda c: isinstance(c, LatteParser.FieldDefContext)
            )
        )
        for field in fields:
            self._load_field(name, field)

    def _load_field(self, name, ctx):
        field_type = ctx.type_().getText()
        for var_ctx in ctx.ID():
            if var_ctx.getText() in self.attrs[name]:
                raise VariableRedeclarationError(ctx)
            self.attrs[name][var_ctx.getText()] = field_type

    def _load_headers(self, ctx):
        name, _ = self._get_cls_and_sup(ctx)
        methods = list(
            ctx.getChildren(
                lambda c: isinstance(c, LatteParser.FunDefContext)
            )
        )
        for method in methods:
            self._load_function_header(name, method)

    def _load_function_header(self, obj, ctx: LatteParser.FunDefContext):
        name = ctx.ID().getText()
        if name in self.methods[obj]:
            raise FunctionRedeclarationError(ctx)
        ret_type = ctx.type_().getText()
        types = ctx.arg().type_() if ctx.arg() else []
        types = [t.getText() for t in types]
        names = ctx.arg().ID() if ctx.arg() else []
        names = [name.getText() for name in names]
        pairs = zip(names, types)
        self.methods[obj][name] = (
            ret_type,
            list(pairs)
        )

    def _get_cls_and_sup(self, ctx):
        if isinstance(ctx, LatteParser.BaseClassDefContext):
            return ctx.ID().getText(), self.OBJECT
        return ctx.ID(0).getText(), ctx.ID(1).getText()

    def build_vtables(self):
        for cls in self.classes:
            self.vtables[cls] = self.get_vtable(cls)

    def get_vtable(self, cls):
        vtable, ancestors = OrderedDict(), []
        while cls is not None:
            ancestors.append(cls)
            cls = self.classes[cls]
        for cls in ancestors[::-1]:
            for method in self.methods[cls]:
                vtable[method] = cls
        return [(m, cls) for cls, m in vtable.items()]