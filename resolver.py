from astnodes import *
from typenodes import *
from dataclasses import dataclass, field
from typing import Union


@dataclass
class Scope:
    variables: dict[str, Local] = field(default_factory=dict)
    top: int = 0
    prev: "Union[Scope, None]" = None

    def find(self, name: str) -> Union[Local, None]:
        if name in self.variables:
            return self.variables[name]
        elif self.prev is not None:
            return self.prev.find(name)
        else:
            return None

    def add_local(self, name: str, typ: Type):
        self.top += typ.sizeof()
        local = Local(
            addr=self.top,
            typ=typ,
        )
        self.variables[name] = local
        return local


@dataclass
class Resolver:
    functions: dict[str, Fun] = field(default_factory=dict)
    strings: list[str] = field(default_factory=list)
    cur_fun: Global = None
    scope: Scope = None
    # globals_: dict[str, Global] = field(default_factory=dict)

    # def add_global(self, name: str, typ: Type):
    #     if name not in self.globals_:
    #         self.globals_[name] = Global(typ=typ, name=name)
    #     else:
    #         raise ResolverError(f"global '{name}' ya declarada")

    def resolve(self, ast: Node) -> Type:
        ast.resolve(self)
        return self

    def add_local(self, name: str, typ: Type) -> None:
        if self.cur_fun is None:
            raise Exception("no se puede usar 'add_local' en contexto global")
        self.scope.add_local(name, typ)
        self.cur_fun.max_size = max(self.scope.top, self.cur_fun.max_size)

    def add_string(self, string: str) -> int:
        self.strings.append(string)
        return len(self.strings)

    def find_var(self, name: str) -> Union[Local, Global, None]:
        return (
            self.scope is not None
            and self.scope.find(name)
            # or self.globals.get(name, None)
            or None
        )

    def init(self, name: str) -> None:
        var = self.find_var(name)
        if var is not None:
            var.initialized = True

    def is_declared(self, name: str) -> bool:
        return self.find_var(name) is not None

    def is_declared_in_scope(self, name: str) -> bool:
        if self.scope is None:
            # return name in self.globals <= TODO
            return False
        else:
            return name in self.scope.variables

    def is_initialized(self, name: str) -> bool:
        var = self.find_var(name)
        return var is not None and var.initialized


class ResolverError(Exception):
    ...


# --- Expressions --- #


@monkeypatch(NumExp)
def resolve(self, _):
    return TypeInt


@monkeypatch(StrExp)
def resolve(self, _):
    return TypePtr(TypeChar)


@monkeypatch(VarExp)
def resolve(self: VarExp, res: Resolver):
    var = res.find_var(self.lit)
    if var is None:  # = no declarada aún
        raise ResolverError(f"variable '{self.lit}' no declarada")

    if not var.initialized:
        raise ResolverError(f"variable '{self.lit}' no initializada")

    self.resolved_as = var
    return var.typ


@monkeypatch(UnaryExp)
def resolve(self: UnaryExp, res: Resolver):
    t = self.exp.resolve(res)

    if self.op == "&":
        return TypePtr(t)

    return t


@monkeypatch(BinaryExp)
def resolve(self: BinaryExp, res: Resolver):
    _t1 = self.exp1.resolve(res)
    _t2 = self.exp2.resolve(res)
    return TypeInt


@monkeypatch(CallExp)
def resolve(self: CallExp, res: Resolver):
    fun: Fun = res.functions.get(self.callee, None)

    if fun is None:
        raise ResolverError(f"función '{self.lit}' no declarada")

    for tparam, arg in zip(fun.typ.params, self.args):
        targ: Type = arg.resolve(res)

        if targ != tparam:
            raise ResolverError(
                f"función tomó argumento de tipo {targ}, pero se necesita tipo {tparam}"
            )

    return fun.typ.ret


@monkeypatch(AssignExp)
def resolve(self: AssignExp, res: Resolver):
    var = res.find_var(self.var.lit)
    if var is None:  # = no declarada aún
        raise ResolverError(f"variable '{self.lit}' no declarada")
    self.var.resolved_as = var

    t = self.exp.resolve(res)
    if var.typ != t:
        raise ResolverError(
            f"variable '{self.var.lit}' es de tipo {tvar}, pero se está asignando una expresión de tipo {var.typ}"
        )
    var.initialized = True

    return var.typ


# --- Statements --- #


@monkeypatch(ExpStmt)
def resolve(self, res: Resolver):
    self.exp.resolve(res)


@monkeypatch(ReturnStmt)
def resolve(self, res: Resolver):
    tret = res.cur_fun.typ.ret

    if self.exp is not None:
        if tret == TypeVoid:
            raise ResolverError("no se puede devolver valores desde funciones void")

        t = self.exp.resolve(res)
        if t != tret:
            raise ResolverError(
                f"se quiere devolver una expresión de tipo {t} en una función que devuelve {tret}"
            )

    elif tret != TypeVoid:
        raise ResolverError(
            "se intenta retornar de una función no void sin una expresión"
        )


@monkeypatch(VarStmt)
def resolve(self: VarStmt, res: Resolver):
    tbase = self.base_type
    for name, exp in self.vars:
        if res.is_declared_in_scope(name):
            raise ResolverError(f"variable '{name}' ya declarada en scope actual")

        tvar = tbase

        res.add_local(name, tvar)
        if exp is not None:
            texp = exp.resolve(res)
            if texp != tvar:
                raise ResolverError(
                    f"se pretende asignar a variable '{name}' con expresión de tipo {texp}, se espera tipo {tvar}"
                )
            res.init(name)


@monkeypatch(PrintfStmt)
def resolve(self, res: Resolver):
    # TODO: cambiar para cuando se añadan más tipos
    if self.fmt.count("%i") != len(self.args):
        raise ResolverError(
            f"printf no tiene la misma cantidad de argumentos que de signos de formato"
        )

    targs = []
    for arg in self.args:
        t = arg.resolve(res)
        targs.append(t)

        if t != TypeInt:
            raise ResolverError(
                f"no se pueden pasar valores no enteros a printf después del formato"
            )

    tstr = StrExp(self.fmt).resolve(res)
    self.stack_size = sum(t.sizeof() for t in targs) + tstr.sizeof()


@monkeypatch(ScanfStmt)
def resolve(self: ScanfStmt, res: Resolver):
    if self.fmt.count("%i") != len(self.args):
        raise ResolverError(
            f"printf no tiene la misma cantidad de argumentos que de signos de formato"
        )

    targs = []
    intptr = TypePtr(TypeInt)
    for arg in self.args:
        t = arg.resolve(res)
        targs.append(t)

        if t != intptr:
            raise ResolverError(
                f"no se pueden pasar valores no punteros de enteros a scanf después del formato"
            )

    tstr = StrExp(self.fmt).resolve(res)
    self.stack_size = sum(t.sizeof() for t in targs) + tstr.sizeof()


# --- Top Level --- #


@monkeypatch(FunDeclTop)
def resolve(self: FunDeclTop, res: Resolver):
    if self.name in res.functions:
        raise ResolverError(f"función '{self.name}' ya declarada")

    res.functions[self.name] = Fun(
        name=self.name,
        typ=self.sig,
        params=self.params,
        arg_space=sum(arg.sizeof() for arg in self.sig.params),
    )


@monkeypatch(FunDefTop)
def resolve(self: FunDefTop, res: Resolver):
    name = self.head.name

    if res.is_initialized(name):
        raise ResolverError(
            f"{'función' if res.is_fun(name) else 'variable'} '{name}' ya definida"
        )

    elif res.is_declared(name):
        # si se ha declarado 'name', pero
        # no hay ninguna función llamada 'name', entonces
        # es una variable ya existente
        fun = res.functions.get(name, None)
        if fun is None:
            raise ResolverError(f"variable '{name}' ya existente")

        fun.params = self.head.params
        if fun.typ != self.head.sig:
            raise ResolverError(
                f"tipo de la definición de la función '{name}' no es la misma que la de su declaración"
            )

    else:
        self.head.resolve(res)

    res.cur_fun = res.functions[name]
    fun: Fun = res.cur_fun
    fun.initialized = True

    vars = {}

    for i, param in enumerate(zip(fun.typ.params, fun.params)):
        typ, param = param
        vars[param] = Local(
            initialized=True,
            typ=typ,
            addr=8 + i * 4,
        )
    res.scope = Scope(variables=vars)

    for stmt in self.body:
        stmt.resolve(res)

    res.cur_fun = None
    res.scope = None


@monkeypatch(Program)
def resolve(self: Program, res: Resolver):
    for topdecl in self.topdecls:
        topdecl.resolve(res)
