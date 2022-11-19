from dataclasses import dataclass, field
from typenodes import *
from typing import Tuple, Optional, Union


def monkeypatch(cls):
    def decor(f):
        setattr(cls, f.__name__, f)
        return f

    return decor


# --- Auxiliares --- #


@dataclass
class TopObject:
    initialized: bool = False
    typ: Type = None


@dataclass
class Local(TopObject):
    addr: int = 0


@dataclass
class Global(TopObject):
    name: str = ""


@dataclass
class Fun(TopObject):
    name: str = ""
    params: list[str] = field(default_factory=list)
    max_stack_size: int = 0
    arg_space: int = 0


# --- Nodos --- #


class Node:
    ...


# Expresiones


@dataclass
class VarExp(Node):
    lit: str
    resolved_as: Local = None

    def __str__(self):
        return self.lit


@dataclass
class StrExp(Node):
    lit: str

    def __str__(self):
        return f'"{self.lit}"'


@dataclass
class NumExp(Node):
    lit: int

    def __str__(self):
        return str(self.lit)


@dataclass
class UnaryExp(Node):
    op: str  # = !, -, &, *
    exp: Node

    def __str__(self):
        return f"{self.op} ({self.exp})"


@dataclass
class BinaryExp(Node):
    exp1: Node
    op: str  # = ||, &&, +, -, *, /
    exp2: Node

    def __str__(self):
        return f"({self.exp1}) {self.op} ({self.exp2})"


@dataclass
class ArrayPosExp(Node):
    exp: Node
    offset: int

    def __str__(self):
        return f"{self.exp}[{self.offset}]"


@dataclass
class CallExp(Node):
    callee: str
    args: list[Node]

    def __str__(self):
        args = ", ".join(map(str, self.args))
        return f"{self.callee}({args})"


@dataclass
class AssignExp(Node):
    var: Node
    exp: Node

    def __str__(self):
        return f"{self.var} = {self.exp}"


# Declaraciones


@dataclass
class VarStmt(Node):
    base_type: Type
    vars: list[Tuple[Type, str, Union[Node, None]]]

    def __str__(self):
        vars = ", ".join(
            (var if exp is None else f"{var} = {exp}" for var, exp in self.vars)
        )
        return f"{self.var_type} {vars};"


@dataclass
class ExpStmt(Node):
    exp: Node

    def __str__(self):
        return f"{self.exp};"


@dataclass
class ReturnStmt(Node):
    exp: Union[Node, None]

    def __str__(self):
        if self.exp is None:
            return "return;"
        else:
            return f"return {self.exp};"


@dataclass
class PrintfStmt(Node):
    fmt: str
    args: list[Node]
    stack_size: int = 0

    def __str__(self):
        args = ", ".join(map(str, self.args))
        return f"printf({self.fmt}, {args})"


@dataclass
class ScanfStmt(Node):
    fmt: str
    args: list[Node]
    stack_size: int = 0

    def __str__(self):
        args = ", ".join(map(str, self.args))
        return f"scanf({self.fmt}, {args})"


# Toplevel


@dataclass
class FunDeclTop(Node):
    name: str
    sig: TypeFun
    params: list[str]


@dataclass
class FunDefTop(Node):
    head: FunDeclTop
    body: list[Node]


@dataclass
class Program(Node):
    topdecls: list[Node]
