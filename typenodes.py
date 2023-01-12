from dataclasses import dataclass, field
from typing import Union
import copy


@dataclass
class Type:
    lvalue: bool = False
    const: bool = False

    # fmt: off
    def is_lvalue(self) -> bool: return self.lvalue
    def is_rvalue(self) -> bool: return not self.lvalue
    def is_const(self) -> bool: return self.const
    def sizeof(self) -> int: return 0
    def is_ptr(self) -> bool: return False
    def as_ptr(self) -> "Type": return TypePtr(inner=self)
    def as_array(self, size: int) -> "Type": return TypeArray(inner=self, size=size)
    def __eq__(self, typ) -> bool: return False
    # fmt: on

    def dup(self, is_lvalue: bool = False, is_const: bool = None) -> "Type":
        d = copy.copy(self)
        d.lvalue = is_lvalue
        if is_const is not None:
            d.const = is_const
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
class TypeBuiltin(Type):
    name: str = ""
    size: int = 4

    def __str__(self) -> str:
        return self.name

    def sizeof(self) -> int:
        return self.size

    def __eq__(self, typ):
        return isinstance(typ, TypeBuiltin) and typ.name == self.name


@dataclass
class TypePtr(Type):
    inner: Type = None

    def __str__(self) -> str:
        return f"{self.inner}*"

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

    def __str__(self) -> str:
        return f"{self.inner}[{self.size}]"

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

    def __str__(self) -> str:
        return f"{self.ret}(*)({', '.join(map(str, self.params))})"

    def __eq__(self, typ):
        return (
            isinstance(typ, TypeFun)
            and typ.params == self.params
            and typ.ret == self.ret
        )


TypeVoid = TypeBuiltin(name="void", size=1)
TypeChar = TypeBuiltin(name="char", size=1)
TypeInt = TypeBuiltin(name="int", size=4)
TypeFloat = TypeBuiltin(name="float", size=4)
