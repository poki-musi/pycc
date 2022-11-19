from dataclasses import dataclass, field

@dataclass
class Type:
    def sizeof(self) -> int:
        return 0

    def __eq__(self, typ) -> bool:
        return False

    def __ne__(self, typ) -> bool:
        return not (self == typ)

@dataclass
class TypeName(Type):
    name: str
    size: int = 4

    def sizeof(self) -> int:
        return self.size

    def __str__(self): return self.name

    def __eq__(self, typ):
        return isinstance(typ, TypeName) and typ.name == self.name

@dataclass
class TypePtr(Type):
    inner: Type

    def sizeof(self) -> int:
        return 4 # ptr size in bytes

    def __str__(self): return f"{self.inner}*"

    def __eq__(self, typ):
        return isinstance(typ, TypePtr) and typ.inner == self.inner

@dataclass
class TypeArray(Type):
    inner: Type
    size: int

    def sizeof(self) -> int:
        return self.inner.size() * self.size

    def __getitem__(self, addr) -> int:
        return self.inner.sizeof() * addr

    def __str__(self):
        return f"{self.inner}[{self.size}]"

    def __eq__(self, typ):
        return isinstance(typ, TypePtr) and typ.inner == self.inner

    def __eq__(self, typ):
        return isinstance(typ, TypeArray) and typ.size == self.size and typ.inner == self.inner

@dataclass
class TypeFun(Type):
    params: list[Type]
    ret: Type

    def sizeof(self) -> int:
        return 4 # ptr size in bytes

    def __str__(self):
        return f"{self.ret}(*)({', '.join(map(str, self.params))})"

    def __eq__(self, typ):
        return isinstance(typ, TypeFun) and typ.params == self.params and typ.ret == self.ret

TypeVoid = TypeName(name="void", size=0)
TypeInt = TypeName("int")
