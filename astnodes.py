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


@dataclass
class StrExp(Node):
    lit: str


@dataclass
class NumExp(Node):
    lit: int


@dataclass
class UnaryExp(Node):
    op: str  # = !, -, &, *
    exp: Node


@dataclass
class BinaryExp(Node):
    exp1: Node
    op: str  # = ||, &&, +, -, *, /
    exp2: Node


@dataclass
class ArrayPosExp(Node):
    exp: Node
    offset: Node


@dataclass
class CallExp(Node):
    callee: str
    args: list[Node]


@dataclass
class AssignExp(Node):
    var: Node
    exp: Node


# Declaraciones


@dataclass
class VarStmt(Node):
    vars: list[Tuple[Type, VarExp, Union[Node, None]]]


@dataclass
class ExpStmt(Node):
    exp: Node


@dataclass
class ReturnStmt(Node):
    exp: Union[Node, None]


@dataclass
class PrintfStmt(Node):
    fmt: str
    args: list[Node]
    stack_size: int = 0


@dataclass
class ScanfStmt(Node):
    fmt: str
    args: list[Node]
    stack_size: int = 0


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
