
"""
Meaningful compilation errors.
"""


class CompilationError(Exception):
    name = 'Compilation Error'
    msg = ''

    def __init__(self, ctx, msg=''):
        self.ctx = ctx
        self.msg = msg

    def __str__(self):
        return f'{self.name} at line {self.ctx.start.line}!\n'\
               f'{self.msg}'


class TypeMismatchError(CompilationError):
    name = 'Type Mismatch Error'


class BadConditionError(CompilationError):
    name = "Bad Condition Error"


class UnknownTypeError(CompilationError):
    name = "Unknown Type Error"


class UnknownArgumentTypeError(CompilationError):
    name = "Unknown Argument Type Error"


class UnknownReturnTypeError(CompilationError):
    name = "Unknown Return Type Error"


class UndeclaredVariableError(CompilationError):
    name = "Undeclared Variable Error"


class UndeclaredFunctionError(CompilationError):
    name = "Undeclared Function Error"


class UndeclaredClassError(CompilationError):
    name = "Undeclared Class Error"


class UnsupportedOperandError(CompilationError):
    name = 'Unsupported Operand Error'


class FunctionRedeclarationError(CompilationError):
    name = 'Function Redeclaration Error'

    # def __init__(self, ctx):
    #     super().__init__(ctx)
    #     self.msg = f'A function with name {ctx.ID().getText()} is declared.'


class ClassRedeclarationError(CompilationError):
    name = 'Class Redeclaration Error'

    # def __init__(self, ctx):
    #     super().__init__(ctx)
    #     self.msg = f'A class with name {ctx.ID().getText()} is declared.'


class VariableRedeclarationError(CompilationError):
    name = 'Variable Redeclaration Error'


class MissingAttributeError(CompilationError):
    name = "Missing Attribute Error"


class MissingMainFunctionError(CompilationError):
    name = "Missing Main Function Error"


class InvalidReturnTypeError(CompilationError):
    name = "Invalid Return Type Error"


class ArgumentMismatchError(CompilationError):
    name = 'Argument Mismatch Error'


class InvalidCastError(CompilationError):
    name = 'Invalid Cast Error'


class CyclicInheritanceError(CompilationError):
    name = "Cyclic Inheritance Error"


class UnreachableReturnError(CompilationError):
    name = "Unreachable Return Error"


class InvalidReferenceError(CompilationError):
    name = "Invalid Reference Error"


class BadOverrideError(CompilationError):
    name = "Bad Override Error"


class ArraysNotImplemented(CompilationError):
    name = "Arrays Not Implemented"
