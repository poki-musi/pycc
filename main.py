import os
from parser import CParser, CLexer, ParserError
from resolver import Resolver, ResolverError
from compiler import Compiler, CompilerError
from datetime import datetime


def process_file(inp):
    tokens = CLexer().tokenize(inp)
    ast = CParser().parse(tokens)
    res = Resolver().resolve(ast)
    return Compiler.of_resolver(res).compile(ast).generate()

def run_tests(fh):
    log = fh.write

    for file in next(os.walk("examples/pass"))[2]:
        with open(f"examples/pass/{file}", "r") as f:
            try:
                log("== " * 10 + "pass/" + file + " ==" * 10)
                log(process_file(f.read()))
            except (ParserError, ResolverError, CompilerError) as e:
                log(str(e))

    for file in next(os.walk("examples/error"))[2]:
        with open(f"examples/error/{file}", "r") as f:
            try:
                log("== " * 10 + "error/" + file + " ==" * 10, file=fh)
                log(process_file(f.read()))
            except (ParserError, ResolverError, CompilerError) as e:
                log(str(e))


def main():
    try:
        os.mkdir("./out")
    except:
        pass

    with open(f"out/{datetime.now()}.log", "w") as fh:
        print("here")
        run_tests(fh)


if __name__ == "__main__":
    main()
