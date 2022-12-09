import os
import sys
import pprint
from parser import CParser, CLexer, ParserError
from resolver import Resolver, ResolverError
from compiler import Compiler
from datetime import datetime


def process_file(inp):
    print("-- Parser")
    tokens = CLexer().tokenize(inp)
    ast = CParser().parse(tokens)
    print("-- Resolver")
    res = Resolver().resolve(ast)
    print("-- Compiler")
    asm = Compiler.of_resolver(res).compile(ast).generate()
    return asm

def run_tests(log, err):
    for file in next(os.walk("examples/pass"))[2]:
        with open(f"examples/pass/{file}", "r") as f:
            try:
                err("== " * 10 + "pass/" + file + " ==" * 10)
                log("== " * 10 + "pass/" + file + " ==" * 10)
                log(process_file(f.read()))
            except (ParserError, ResolverError) as e:
                log(str(e))
                err(str(e))

    for file in next(os.walk("examples/error"))[2]:
        with open(f"examples/error/{file}", "r") as f:
            try:
                err("== " * 10 + "error/" + file + " ==" * 10)
                log("== " * 10 + "error/" + file + " ==" * 10)
                log(process_file(f.read()))
            except (ParserError, ResolverError) as e:
                log(str(e))
                err(str(e))


def main():
    try:
        os.mkdir("./out")
    except:
        pass

    run_tests(print, lambda a: a)


if __name__ == "__main__":
    main()
