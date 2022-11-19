from astnodes import *
from typenodes import *
from resolver import Resolver
from dataclasses import dataclass, field
from typing import Union


@dataclass
class Reg:
    name: str

    def __add__(self, o):
        if o == 0:
            return self.name
        else:
            return f"{o}(%{self.name})"

    def __sub__(self, o):
        return self.__add__(-o)

    def __str__(self):
        return self.name


EAX = Reg("eax")
EBX = Reg("ebx")
EBP = Reg("ebp")
ESP = Reg("esp")


def S(n):
    return f"${n}"


@dataclass
class Compiler:
    functions: dict[str, Fun]
    prelude: dict[str, None] = field(default_factory=dict)
    cur_fun: Fun = None
    asm: list[str] = field(default_factory=list)

    @staticmethod
    def of_resolver(res: Resolver):
        return Compiler(functions=res.functions)

    def compile(self, ast: Node):
        ast.compile(self)
        return self

    def generate(self):
        return "\n".join(self.asm)

    def var(self, name: str) -> Union[int, None]:
        if name in self.cur_fun.locals_:
            return EBX - self.cur_fun.locals_[name].addr

        try:
            idx = self.cur_fun.params.index(name)
            return EBX + (8 + 4 * idx)
        except ValueError:
            pass

        if name in self.globals_:
            return self.globals_[name].addr

        return None

    # --- Instruction DSL --- #

    def add_line(self, line):
        self.asm.append("    " + line)

    def label(self, label):
        self.asm.append(label + ":")

    def nl(self):
        self.add_line("")

    def addl(self, orig, to):
        self.add_line(f"addl {orig}, {to}")

    def subl(self, orig, to):
        self.add_line(f"subl {orig}, {to}")

    def imull(self, orig, to):
        self.add_line(f"imull {orig}, {to}")

    def cdq(self):
        self.add_line("cdq")

    def idivl(self, orig):
        self.add_line(f"idivl {orig}")

    def pushl(self, reg):
        self.add_line(f"pushl {reg}")

    def popl(self, reg):
        self.add_line(f"popl {reg}")

    def movl(self, orig, to):
        self.add_line(f"movl {orig}, {to}")

    def neg(self, orig):
        self.add_line(f"neg {orig}")

    def call(self, label):
        self.add_line(f"call {label}")

    def ret(self):
        self.add_line("ret")

    def emit_return(self):
        self.movl(EBP, ESP)
        self.popl(EBP)
        self.ret()


class CompilerError(Exception):
    ...


@monkeypatch(Node)
def compiler(self, _):
    pass


# --- Expressions --- #


@monkeypatch(VarExp)
def compile(self: VarExp, cmp: Compiler):
    cmp.movl(cmp.var(self.lit), EAX)


@monkeypatch(NumExp)
def compile(self: NumExp, cmp: Compiler):
    cmp.movl(S(self.lit), EAX)


@monkeypatch(StrExp)
def compile(self: StrExp, cmp: Compiler):
    addr = cmp.add_string(self.lit)
    cmp.movl(addr, EAX)


@monkeypatch(UnaryExp)
def compile(self: UnaryExp, cmp: Compiler):
    self.exp.compile(cmp)

    if self.op == "-":
        cmp.neg(EAX)


@monkeypatch(BinaryExp)
def compile(self: BinaryExp, cmp: Compiler):
    if self.op == "||":
        self.exp1.compile(cmp)
    if self.op == "&&":
        self.exp1.compile(cmp)
    else:
        self.exp1.compile(cmp)
        cmp.pushl(EAX)

        self.exp2.compile(cmp)
        cmp.movl(EAX, EBX)
        cmp.popl(EAX)

        if self.op == "+":
            cmp.addl(EBX, EAX)
        elif self.op == "-":
            cmp.subl(EBX, EAX)
        elif self.op == "*":
            cmp.imull(EBX, EAX)
        elif self.op == "/":
            cmp.cdq()
            cmp.idivl(EBX)


@monkeypatch(AssignExp)
def compile(self: AssignExp, cmp: Compiler):
    self.exp.compile(cmp)
    cmp.movl(EAX, cmp.var(self.var))


@monkeypatch(CallExp)
def compile(self: CallExp, cmp: Compiler):
    for arg in reversed(self.args):
        arg.compile(cmp)
        cmp.pushl(EAX)
    cmp.call(self.callee)
    if len(self.args) > 0:
        cmp.addl(S(4 * len(self.args)), ESP)


# --- Statements --- #


@monkeypatch(ExpStmt)
def compile(self, cmp: Compiler):
    self.exp.compile(cmp)


@monkeypatch(VarStmt)
def compile(self: VarStmt, cmp: Compiler):
    fun = cmp.cur_fun
    for name, exp in self.vars:
        if exp is not None:
            exp.compile(cmp)
            cmp.movl(EAX, cmp.var(name))


@monkeypatch(ReturnStmt)
def compile(self: ReturnStmt, cmp: Compiler):
    if self.exp is not None:
        self.exp.compile(cmp)
    else:
        cmp.movl(S(0), EAX)
    cmp.emit_return()


@monkeypatch(PrintfStmt)
@monkeypatch(ScanfStmt)
def compile(self: ScanfStmt, cmp: Compiler):
    CallExp(
        callee="scanf" if isinstance(self, ScanfStmt) else "printf",
        args=[self.fmt, *self.args],
    ).compile(cmp)


# --- Top Level --- #


@monkeypatch(FunDeclTop)
def compile(self: FunDeclTop, cmp: Compiler):
    pass


@monkeypatch(FunDefTop)
def compile(self: FunDefTop, cmp: Compiler):
    name = self.head.name

    cmp.add_line(".text")
    cmp.add_line(f".globl {name}")
    cmp.add_line(f".type {name}, @function")
    cmp.label(name)

    fun: Fun = cmp.globals_[name]
    cmp.cur_fun = fun

    cmp.pushl(EBP)
    cmp.movl(ESP, EBP)
    if cmp.cur_fun.locals_:
        # si hay locales, hacer espacio
        cmp.subl(S(len(fun.locals_) * 4), ESP)
    cmp.nl()

    for stmt in self.body:
        for line in str(stmt).split("\n"):
            cmp.add_line("; " + line)
        stmt.compile(cmp)
        cmp.nl()

    # TODO devuelve 0 por defecto por ahora

    if cmp.cur_fun.typ.ret == TypeInt:
        cmp.movl(S(0), EAX)
    cmp.emit_return()
    cmp.nl()


@monkeypatch(Program)
def compile(self: Program, cmp: Compiler):
    for topdecl in self.topdecls:
        topdecl.compile(cmp)
