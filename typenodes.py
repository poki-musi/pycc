from dataclasses import dataclass, field
from typing import Union
import copy


@dataclass
class Type:
    lvalue: bool = True

    # fmt: off
    def is_lvalue(self): return self.lvalue
    def is_rvalue(self): return not self.lvalue
    def sizeof(self) -> int: return 0
    def __eq__(self, typ) -> bool: return False
    def dup(self) -> "Type": return copy.copy(self)
    # fmt: on


@dataclass
class TypeName(Type):
    name: str = ""
    size: int = 4

    def sizeof(self) -> int:
        return self.size

    def __str__(self):
        return self.name

    def __eq__(self, typ):
        return isinstance(typ, TypeName) and typ.name == self.name


@dataclass
class TypePtr(Type):
    inner: Type = None

    def sizeof(self) -> int:
        return 4  # ptr size in bytes

    def __str__(self):
        return f"{self.inner}*"

    def __eq__(self, typ):
        return isinstance(typ, TypePtr) and typ.inner == self.inner


@dataclass
class TypeArray(Type):
    inner: Type = None
    size: int = 0

    def sizeof(self) -> int:
        return self.inner.sizeof() * self.size

    def __getitem__(self, addr) -> int:
        return self.inner.sizeof() * addr

    def __str__(self):
        return f"{self.inner}[{self.size}]"

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

    def sizeof(self) -> int:
        return 4  # ptr size in bytes

    def __str__(self):
        return f"{self.ret}(*)({', '.join(map(str, self.params))})"

    def __eq__(self, typ):
        return (
            isinstance(typ, TypeFun)
            and typ.params == self.params
            and typ.ret == self.ret
        )


TypeVoid = TypeName(name="void", size=0)
TypeInt = TypeName(name="int", size=4)
TypeChar = TypeName(name="char", size=1)
