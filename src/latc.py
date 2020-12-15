import argparse
import os
import subprocess

from antlr4 import FileStream, CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener

from assembly_generator import AssemblyGenerator
from assembly_writer import AssemblyWriter
from errors import CompilationError
from error_checker import ErrorChecker
from expression_evaluator import ExpressionEvaluator
from latte_state import LatteStateLoader
from locals_counter import LocalsCounter
from peephole_optimizer import PeepholeOptimizer
from return_checker import ReturnAbilityChecker
from string_finder import StringFinder
from tree_optimizer import TreeOptimizer

from antlr4gen.LatteLexer import LatteLexer
from antlr4gen.LatteParser import LatteParser


class LatteErrorListener(ErrorListener):
    """ Error listener for antlr4 errors. """
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise SyntaxError(
            f"Syntax Error at line {line} and column {column}.\n"
            f'Error message: {msg}.'
        )


def compile(filepath: str, opt_tree: bool, peephole: bool):
    fs = FileStream(filepath)
    lexer = LatteLexer(fs)
    stream = CommonTokenStream(lexer)
    parser = LatteParser(stream, )

    parser.removeErrorListeners()
    parser.addErrorListener(LatteErrorListener())

    try:
        tree = parser.program()

        loader = LatteStateLoader()
        loader.load(tree)

        error_checker = ErrorChecker()
        error_checker.set_state(*loader.get_state())
        error_checker.visit(tree)

        expression_evaluator = ExpressionEvaluator()
        expression_evaluator.visit(tree)

        ret_checker = ReturnAbilityChecker()
        ret_checker.visit(tree)

        if opt_tree:
            tree_optimizer = TreeOptimizer()
            tree_optimizer.visit(tree)

        locals_counter = LocalsCounter()
        locals_counter.visit(tree)

        string_finder = StringFinder()
        string_finder.visit(tree)

        writer = AssemblyWriter()
        code_gen = AssemblyGenerator(string_finder.get_strings(), writer)
        code_gen.set_state(*loader.get_state())
        code_gen.visit(tree)

        if peephole:
            po = PeepholeOptimizer(writer)
            po.optimize()

        print('OK', file=os.sys.stderr)
        return writer.get_code()

    except CompilationError as e:
        print('ERROR', file=os.sys.stderr)
        print(str(e))
        raise SystemExit(1)
    except Exception as e:
        print('ERROR', file=os.sys.stderr)
        print(str(e))
        raise SystemExit(1)


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def main():
    parser = argparse.ArgumentParser(description="Latte compiler.")
    parser.add_argument(
        '--peephole', type=str2bool, default=True,
        help='[T/F] if peephole optimization should be performed.'
    )
    parser.add_argument(
        '--const_expr', type=str2bool, default=True,
        help='[T/F] if constant expression optimization should be performed.'
    )
    parser.add_argument(
        'filepath', nargs=1, type=str, help='Path of the file to compile.'
    )
    args = parser.parse_args()
    path = os.path.abspath(os.getcwd())
    path = os.path.join(path, args.filepath[0])

    code = compile(path, args.const_expr, args.peephole)

    base_file = os.path.splitext(path)[0]

    with open(base_file + '.asm', 'w') as f:
        f.write(code)

    here = os.path.dirname(os.path.abspath(__file__))
    runtime_path = os.path.join(here, '../lib/runtime.o')
    subprocess.call(
        f'nasm -f Elf32 -o {base_file}.o {base_file}.asm',
        shell=True
    )
    subprocess.call(
        f'gcc -m32 {runtime_path} {base_file}.o -o {base_file}.out',
        shell=True
    )


if __name__ == '__main__':
    main()
