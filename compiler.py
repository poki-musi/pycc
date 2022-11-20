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
            return f"(%{self.name})"
        else:
            return f"{o}(%{self.name})"

    def __sub__(self, o):
        return self.__add__(-o)

    def __str__(self):
        return self.name

    def deref(self):
        return f"(%{self.name})"


EAX = Reg("eax")
EBX = Reg("ebx")
EBP = Reg("ebp")
ESP = Reg("esp")


@monkeypatch(Local)
def reg(self: Local) -> str:
    return EBP - self.addr


@monkeypatch(Global)
def reg(self: Global) -> str:
    return self.name


def S(n):
    return f"${n}"


@dataclass
class Compiler:
    functions: dict[str, Fun]
    cur_fun: Fun = None
    label_count: int = 0
    globals: list[None] = field(default_factory=list)  # TODO
    constants: list[str] = field(default_factory=list)
    asm: list[str] = field(default_factory=list)

    @staticmethod
    def of_resolver(res: Resolver):
        return Compiler(functions=res.functions)

    def compile(self, ast: Node):
        ast.compile(self)
        return self

    def generate(self):
        def gen():
            if self.globals:
                yield from self.globals
                yield ""

            if self.constants:
                yield " " * 4 + ".section  .rodata"
                yield from self.constants
                yield ""
            yield from self.asm

        return "\n".join(gen())

    # --- Auxiliar Methods --- #

    def make_label(self, string: str) -> str:
        off = self.label_count
        self.label_count += 1
        return string + str(off)

    def add_line(self, line):
        self.asm.append("    " + line)

    def label(self, label):
        self.asm.append(label + ":")

    def add_string(self, string: str) -> str:
        label = "." + self.make_label("L")
        self.constants.append(label)
        self.constants.append(f"    .string {string}")
        return label

    def add_float(self, num: float) -> str:
        self.label(self.make_label("L"))
        self.add_line(f'.float "{num}"')

    def nl(self):
        self.add_line("")

    def emit_return(self):
        self.movl(EBP, ESP)
        self.popl(EBP)
        self.ret()

    # fmt: off
    def addl(self, orig, to): self.add_line(f'addl {orig}, {to}')
    def subl(self, orig, to): self.add_line(f'subl {orig}, {to}')
    def imull(self, orig, to): self.add_line(f'imull {orig}, {to}')
    def movl(self, orig, to): self.add_line(f'movl {orig}, {to}')
    def cmpl(self, orig, to): self.add_line(f'cmpl {orig}, {to}')
    def leal(self, orig, to): self.add_line(f'leal {orig}, {to}')

    def idvl(self, arg): self.add_line(f'idvl {arg}')
    def pushl(self, arg): self.add_line(f'pushl {arg}')
    def popl(self, arg): self.add_line(f'popl {arg}')
    def neg(self, arg): self.add_line(f'neg {arg}')
    def call(self, arg): self.add_line(f'call {arg}')

    def j(self, arg): self.add_line(f'j {arg}')
    def je(self, arg): self.add_line(f'je {arg}')
    def jne(self, arg): self.add_line(f'jne {arg}')
    def jge(self, arg): self.add_line(f'jge {arg}')
    def jgt(self, arg): self.add_line(f'jgt {arg}')
    def jle(self, arg): self.add_line(f'jle {arg}')
    def jlt(self, arg): self.add_line(f'jlt {arg}')

    def cdq(self): self.add_line(f'cdq')
    def ret(self): self.add_line(f'ret')
    # fmt: on


# --- Instruction DSL --- #


class CompilerError(Exception):
    ...


# --- Expressions --- #


@monkeypatch(NumExp)
def compile(self: NumExp, cmp: Compiler):
    cmp.movl(S(self.lit), EAX)


@monkeypatch(StrExp)
def compile(self: StrExp, cmp: Compiler):
    label = S(cmp.add_string(self.lit))
    cmp.movl(label, EAX)


@monkeypatch(VarExp)
def compile(self: VarExp, cmp: Compiler):
    cmp.movl(self.resolved_as.reg(), EAX)


@monkeypatch(UnaryExp)
def compile(self: UnaryExp, cmp: Compiler):
    if self.op == "&":
        if isinstance(self.exp, VarExp):
            cmp.leal(self.exp.resolved_as.reg(), EAX)
    else:
        self.exp.compile(cmp)

        if self.op == "-":
            cmp.neg(EAX)
        elif self.op == "*":
            cmp.movl(EAX.deref(), EAX)
        elif self.op == "!":
            label = cmp.make_label(".J")
            cmp.cmpl(S(0), EAX)
            cmp.jne(label)
            cmp.movl(S(0), EAX)
            cmp.label(label)


JUMP_TYPES = {
    "<": "jge",
    ">": "jle",
    ">=": "jlt",
    "<=": "jgt",
    "==": "jne",
    "!=": "je",
}


@monkeypatch(BinaryExp)
def compile(self: BinaryExp, cmp: Compiler):
    if self.op in {"&&", "||"}:
        self.exp1.compile(cmp)
        j = cmp.make_label(".J")
        cmp.cmpl(S(0), EAX)
        if self.op == "&&":
            cmp.je(j)
        else:
            cmp.jne(j)
        self.exp2.compile(cmp)
        cmp.label(j)
        return

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
    else:
        # remaining cases: <, >, <=, >=, ==, !=
        cond_jump = getattr(cmp, JUMP_TYPES[self.op])

        no = cmp.make_label(".J")
        fin = cmp.make_label(".J")
        cmp.cmpl(EBX, EAX)
        cond_jump(no)
        cmp.movl(S(1), EAX)
        cmp.j(fin)

        cmp.label(no)
        cmp.movl(S(0), EAX)
        cmp.label(fin)


@monkeypatch(CallExp)
def compile(self: CallExp, cmp: Compiler):
    # TODO: se asume que callee es un VarExp
    name = self.callee
    fun: Fun = cmp.functions[name.lit]

    for arg in reversed(self.args):
        arg.compile(cmp)
        cmp.pushl(EAX)

    cmp.call(name.lit)
    if fun.arg_space > 0:
        cmp.addl(S(fun.arg_space), ESP)


@monkeypatch(AssignExp)
def compile(self: AssignExp, cmp: Compiler):
    self.exp.compile(cmp)
    cmp.movl(EAX, self.var.resolved_as.reg())


# --- Statements --- #


@monkeypatch(ExpStmt)
def compile(self: ExpStmt, cmp: Compiler):
    self.exp.compile(cmp)


@monkeypatch(VarStmt)
def compile(self: VarStmt, cmp: Compiler):
    for typ, name, exp in self.vars:
        if typ != TypeInt:
            continue  # TODO compilar variables no triviales

        if exp is not None:
            exp.compile(cmp)
            cmp.movl(EAX, name.resolved_as.reg())


@monkeypatch(ReturnStmt)
def compile(self: ExpStmt, cmp: Compiler):
    if self.exp is not None:
        self.exp.compile(cmp)
    cmp.emit_return()


@monkeypatch(PrintfStmt)
@monkeypatch(ScanfStmt)
def compile(self: PrintfStmt, cmp: Compiler):
    for arg in reversed(self.args):
        arg.compile(cmp)
        cmp.pushl(EAX)
    StrExp(self.fmt).compile(cmp)
    cmp.call("printf" if isinstance(self, PrintfStmt) else "scanf")
    cmp.addl(S(self.stack_size), ESP)


# --- Top Level --- #


@monkeypatch(FunDeclTop)
def compile(self: FunDeclTop, cmp: Compiler):
    ...


@monkeypatch(FunDefTop)
def compile(self: FunDefTop, cmp: Compiler):
    name = self.head.name
    fun: Fun = cmp.functions[name]
    bytes_locals = fun.max_stack_size

    cmp.add_line(".text")
    cmp.add_line(f".globl {name}")
    cmp.add_line(f".type {name}, @function")
    cmp.label(name)

    cmp.pushl(EBP)
    cmp.movl(ESP, EBP)
    if bytes_locals != 0:
        cmp.addl(S(bytes_locals), ESP)
    cmp.nl()

    for stmt in self.body:
        stmt.compile(cmp)

    cmp.nl()
    if self.head.sig.ret != TypeVoid:
        cmp.movl(S(0), EAX)  # TODO: para cuando no seamos "monotipo"
    cmp.emit_return()
    cmp.nl()


@monkeypatch(Program)
def compile(self: Program, cmp: Compiler):
    for topstmt in self.topdecls:
        topstmt.compile(cmp)
