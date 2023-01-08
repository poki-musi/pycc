from dataclasses import dataclass, field
from typing import Union
import copy


@dataclass
class Type:
    lvalue: bool = False

    # fmt: off
    def is_lvalue(self) -> bool: return self.lvalue
    def is_rvalue(self) -> bool: return not self.lvalue
    def sizeof(self) -> int: return 0
    def is_ptr(self) -> bool: return False
    def __eq__(self, typ) -> bool: return False
    # fmt: on

    def dup(self, is_lvalue=False) -> "Type":
        d = copy.copy(self)
        d.lvalue = is_lvalue
        return d

    def dup_as_rvalue(self) -> "Type":
        return self.dup(False)

    def dup_as_lvalue(self) -> "Type":
        return self.dup(True)

    def pointify(self, n: int) -> "Type":
        typ = self
        for _ in range(n):
            typ = TypePtr(inner=typ)
        return typ



@dataclass
class TypeName(Type):
    name: str = ""
    size: int = 4

    def sizeof(self) -> int:
        return self.size

    def __eq__(self, typ):
        return isinstance(typ, TypeName) and typ.name == self.name


@dataclass
class TypePtr(Type):
    inner: Type = None

    def sizeof(self) -> int:
        return 4  # ptr size in bytes

    def is_ptr(self) -> bool:
        return True

    def __eq__(self, typ):
        return isinstance(typ, TypePtr) and typ.inner == self.inner


@dataclass
class TypeArray(Type):
    inner: Type = None
    size: int = 0

    def sizeof(self) -> int:
        return self.inner.sizeof() * self.size

    def is_ptr(self) -> bool:
        return True

    def __getitem__(self, addr) -> int:
        return self.inner.sizeof() * addr

    def __eq__(self, typ):
        return isinstance(typ, TypePtr) and typ.inner == self.inner

    def __eq__(self, typ):
        return (
            isinstance(typ, TypeArray)
            and typ.size == self.size
            and typ.inner == self.inner
        )


@dataclass
class TypeFun(Type):
    params: list[Type] = None
    ret: Type = None

    def __eq__(self, typ):
        return (
            isinstance(typ, TypeFun)
            and typ.params == self.params
            and typ.ret == self.ret
        )


TypeVoid = TypeName(name="void", size=0)
TypeInt = TypeName(name="int", size=4)
TypeChar = TypeName(name="char", size=1)
