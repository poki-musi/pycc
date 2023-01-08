import sys
from parser import CParser, CLexer, ParserError
# from resolver import Resolver, ResolverError
# from compiler import Compiler


def process_file(inp):
    tokens = CLexer().tokenize(inp)
    ast = CParser().parse(tokens)
    # res = Resolver().resolve(ast)
    # asm = Compiler.of_resolver(res).compile(ast).generate()
    # return asm
    return ast


def main():
    if len(sys.argv) == 2:
        with open(sys.argv[1], "r") as f:
            data = f.read()
        print(process_file(data))
    else:
        print(
            """
error: se requiere de un fichero de entrada a compilar.

    main.py [fichero].c
"""
        )


if __name__ == "__main__":
    main()
