import os
from parser import CParser, CLexer, ParserError
from resolver import Resolver, ResolverError
from compiler import Compiler, CompilerError


def process_file(inp):
    try:
        tokens = CLexer().tokenize(inp)
        ast = CParser().parse(tokens)
        res = Resolver().resolve(ast)
        return (Compiler
            .of_resolver(res)
            .compile(ast)
            .generate()
        )

    except (ParserError, ResolverError, CompilerError) as e:
        print(e)
        return None  # TODO


def main():
    for file in next(os.walk("examples/"))[2]:
        with open(f"examples/{file}", "r") as f:
            print("== " * 10 + file + " ==" * 10)
            print(process_file(f.read()))


if __name__ == "__main__":
    main()
