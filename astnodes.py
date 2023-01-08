from dataclasses import dataclass, field
from typenodes import *
from typing import Tuple, Optional, Union
from commonitems import *


def monkeypatch(cls):
    def decor(f):
        setattr(cls, f.__name__, f)
        return f

    return decor


# --- Nodos --- #


@dataclass
class Ast:
    pos: int


# Expresiones


@dataclass
class VarExp(Ast):
    lit: str
    resolved_as: Local = None


@dataclass
class StrExp(Ast):
    lit: str


@dataclass
class NumExp(Ast):
    lit: int


@dataclass
class UnaryExp(Ast):
    op: str  # = !, -, &, *
    exp: Ast


@dataclass
class BinaryExp(Ast):
    exp1: Ast
    op: str  # = ||, &&, +, -, *, /
    exp2: Ast


@dataclass
class ArrayPosExp(Ast):
    exp: Ast
    offset: Ast


@dataclass
class ArrayExp(Ast):
    exps: list[Ast]


@dataclass
class CallExp(Ast):
    callee: Ast
    args: list[Ast]


@dataclass
class AssignExp(Ast):
    var: Ast
    exp: Ast


# Declaraciones


@dataclass
class VarDecl(Ast):
    name: str
    num_nested_ptr: int
    size_arrays: list[int]
    exp: Union[Ast, None]


@dataclass
class VarStmt(Ast):
    typ: Type
    vars: list[VarDecl]
    is_static: bool


@dataclass
class ExpStmt(Ast):
    exp: Ast


@dataclass
class ReturnStmt(Ast):
    exp: Union[Ast, None]


@dataclass
class BlockStmt(Ast):
    stmts: list[Ast]


@dataclass
class IfStmt(Ast):
    cond: Ast
    then: BlockStmt
    else_: Union[BlockStmt, None]


@dataclass
class WhileStmt(Ast):
    cond: Ast
    block: Ast


# Toplevel


@dataclass
class FunDeclTop(Ast):
    name: str
    sig: TypeFun
    params: list[str]


@dataclass
class FunDefTop(Ast):
    head: FunDeclTop
    body: list[Ast]
    max_stack_size: int = 0
    resolved_as: Global = None


@dataclass
class VarTop(Ast):
    typ: Type
    vars: list[VarExp]


@dataclass
class Program(Ast):
    topdecls: list[Ast]
