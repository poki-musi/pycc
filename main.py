import sys
from sly.lex import LexError
from parser import CParser, CLexer, ParserError
from resolver import Resolver, ResolverError
from compiler import Compiler
from commonitems import native_functions


def process_file(inp):
    try:
        ast = CParser().parse(CLexer().tokenize(inp))
    except ParserError as e:
        tkn = e.args[0]
        print(f"error:{tkn.lineno}: error de gramática, en token '{tkn.value}'")
        return None

    res = Resolver(globals={**native_functions}).resolve(ast)
    if res.error_state:
        return None

    return Compiler.of_resolver(res).compile(ast).generate()


def main():
    if len(sys.argv) == 2:
        with open(sys.argv[1], "r") as f:
            data = f.read()
        data = process_file(data)
        if data is not None:
            print(data)
    else:
        print(
            """
error: se requiere de un fichero de entrada a compilar.

    main.py [fichero].c
"""
        )


if __name__ == "__main__":
    main()
