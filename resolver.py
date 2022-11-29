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
    cur_fun: Fun = None
    scope: Scope = None

    def resolve(self, ast: Node) -> Type:
        ast.resolve(self)
        return self

    def add_local(self, name: str, typ: Type) -> None:
        if self.cur_fun is None:
            raise Exception("no se puede usar 'add_local' en contexto global")
        local = self.scope.add_local(name, typ)
        self.cur_fun.max_stack_size = max(self.scope.top, self.cur_fun.max_stack_size)
        return local

    def find_var(self, name: str) -> Union[Local, Global, None]:
        return self.scope is not None and self.scope.find(name) or None

    def is_declared(self, name: str) -> bool:
        return self.find_var(name) is not None

    def is_declared_in_scope(self, name: str) -> bool:
        if self.scope is None:
            # return name in self.globals <= TODO
            return False
        else:
            return name in self.scope.variables

    def open_scope(self):
        new_scope = Scope(top=self.scope.top)
        new_scope.prev, self.scope = self.scope, new_scope
        return self.scope

    def close_scope(self):
        self.scope = self.scope.prev
        return self.scope


class ResolverError(Exception):
    ...


# --- Expressions --- #


@monkeypatch(NumExp)
def resolve(self, _):
    return TypeInt


@monkeypatch(StrExp)
def resolve(self, _):
    return TypePtr(lvalue=False, inner=TypeChar)


@monkeypatch(ArrayExp)
def resolve(self: ArrayExp, res: Resolver):
    texps = [exp.resolve(res) for exp in self.exps]

    if not all(a == b for a, b in zip(texps, texps[1:])):
        raise ResolverError("elementos del vector literal no tienen los mismos tipos")

    return TypeArray(inner=texps[0], size=len(texps))


@monkeypatch(VarExp)
def resolve(self: VarExp, res: Resolver):
    var = res.find_var(self.lit)

    if var is None:  # = no declarada aún
        raise ResolverError(f"variable '{self.lit}' no declarada")

    self.resolved_as = var
    var.typ.lvalue = True
    return var.typ


@monkeypatch(UnaryExp)
def resolve(self: UnaryExp, res: Resolver):
    t = self.exp.resolve(res)

    if self.op == "&":
        if t.is_rvalue():
            raise ResolverError(f"se está tomando referencia de un r-valor")
        return TypePtr(lvalue=False, inner=t)

    if self.op == "*":
        if not (isinstance(t, TypePtr) or isinstance(t, TypeArray)):
            raise ResolverError(
                f"se está dereferenciando un valor que no es puntero o vector"
            )
        return t.inner.dup(is_lvalue=True)

    if self.op in {"-", "!"}:
        if t != TypeInt:
            raise ResolverError(
                f"se espera int para el operador {self.op}, pero se encontró {t}"
            )
        return t.dup(is_lvalue=False)


@monkeypatch(BinaryExp)
def resolve(self: BinaryExp, res: Resolver):
    t1 = self.exp1.resolve(res)
    t2 = self.exp2.resolve(res)

    if self.op in {"*", "/", "||", "&&"}:
        if t1 != TypeInt or t2 != TypeInt:
            raise ResolverError(
                f"se esperan tipos enteros para el operador {self.op}, pero se obtuvo {t1} y {t2}"
            )
        return t1.dup(is_lvalue=False)

    if self.op in {"==", "!=", "<=", ">=", "<", ">"}:
        if t1 != t2:
            raise ResolverError(f"no se pueden comparar tipos {t1} y {t2}")
        return TypeInt

    if self.op in {"+", "-"}:
        is_ptr_incr = t1.is_ptr() and t2 == TypeInt or t2.is_ptr() and t1 == TypeInt
        is_num_add = t1 == TypeInt and t2 == TypeInt

        if not (is_ptr_incr or is_num_add):
            raise ResolverError(
                f"se espera puntero y entero o enteros para operador {self.op}, pero se recibió {t1} y {t2}"
            )

        if is_ptr_incr:
            if t1.is_ptr():
                t = t1
                self.exp2 = BinaryExp(
                    exp1=self.exp2, exp2=NumExp(t.inner.sizeof()), op="*"
                )
            else:
                t = t2
                self.exp1 = BinaryExp(
                    exp1=self.exp2, exp2=NumExp(t.inner.sizeof()), op="*"
                )

            return TypePtr(lvalue=False, inner=t1.is_ptr() and t1.inner or t2.inner)
        else:
            return TypeInt.dup(is_lvalue=False)


@monkeypatch(CallExp)
def resolve(self: CallExp, res: Resolver):
    if res.find_var(self.callee) is not None:
        raise ResolverError(
            f"función llamada '{self.callee}' es una variable, no una función"
        )

    fun: Fun = res.functions.get(self.callee, None)
    if fun is None:
        raise ResolverError(f"función '{self.callee.lit}' no declarada")

    for tparam, arg in zip(fun.typ.params, self.args):
        targ: Type = arg.resolve(res)

        if targ != tparam:
            raise ResolverError(
                f"función tomó argumento de tipo {targ}, pero se necesita tipo {tparam}"
            )

    tret = fun.typ.ret.dup()
    tret.lvalue = False
    return tret


@monkeypatch(AssignExp)
def resolve(self: AssignExp, res: Resolver):
    tassign = self.var.resolve(res)
    tval = self.exp.resolve(res)

    if tassign.is_rvalue():
        raise ResolverError("valor al que se asigna no es un lvalor")

    if isinstance(tassign, TypeArray):
        raise ResolverError("valor al que se asigna no puede ser un vector")

    if not tval.coerces_to(tassign):
        raise ResolverError(
            f"valor al que se asigna ({tassign}) no tiene el mismo tipo que la expresión {tval}"
        )

    return tval.dup()


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
    tbase = self.typ
    if tbase == TypeVoid:
        raise ResolverError(f"no pueden existir variables tipo void")

    for var, idxs, exp in self.vars:
        name = var.lit
        if res.is_declared_in_scope(name):
            raise ResolverError(f"variable '{name}' ya declarada en scope actual")

        # convertir el tipo base a un actual tipo array
        typ = tbase.dup()
        for idx in reversed(idxs):
            if idx < 1:
                raise ResolverError(
                    f"variable '{name}' se declaró con un tamaño no estrictamente positivo"
                )
            typ = TypeArray(inner=typ, size=idx)

        if exp is not None:
            texp = exp.resolve(res)
            if isinstance(typ, TypeArray):
                if typ != texp:
                    raise ResolverError(
                        f"se pretende asignar a variable '{name}' con expresión de tipo {texp}, se espera tipo {typ}"
                    )

            elif not texp.coerces_to(typ):
                raise ResolverError(
                    f"se pretende asignar a variable '{name}' con expresión de tipo {texp}, se espera tipo {typ}"
                )

        var.resolved_as = res.add_local(name, typ)


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
    intptr = TypePtr(inner=TypeInt)
    for arg in self.args:
        t = arg.resolve(res)
        targs.append(t)

        if t != intptr:
            raise ResolverError(
                f"no se pueden pasar valores no punteros de enteros a scanf después del formato"
            )

    tstr = StrExp(self.fmt).resolve(res)
    self.stack_size = sum(t.sizeof() for t in targs) + tstr.sizeof()


@monkeypatch(BlockStmt)
def resolve(self: BlockStmt, res: Resolver):
    res.open_scope()
    for stmt in self.stmts:
        stmt.resolve(res)
    res.close_scope()


@monkeypatch(IfStmt)
def resolve(self: IfStmt, res: Resolver):
    tcond = self.cond.resolve(res)
    if not tcond.coerces_to(TypeInt):
        raise ResolverError("la declaración if tiene una condicional que no es entera")

    self.then.resolve(res)

    if self.else_ is not None:
        self.else_.resolve(res)


@monkeypatch(WhileStmt)
def resolve(self: WhileStmt, res: Resolver):
    tcond = self.cond.resolve(res)
    if not tcond.coerces_to(TypeInt):
        raise ResolverError("la declaración if tiene una condicional que no es entera")

    self.block.resolve(res)


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

    fun = res.functions.get(name, None)
    if fun is not None:
        if fun.initialized:
            raise ResolverError(f"función '{name}' ya definida")

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

    off = 8
    for typ, param in zip(fun.typ.params, fun.params):
        if param in vars:
            raise ResolverError(f"parámetro '{param}' ya declarado")

        vars[param] = Local(
            typ=typ,
            addr=-off,
        )
        off += typ.sizeof()
    res.scope = Scope(variables=vars)

    for stmt in self.body:
        stmt.resolve(res)

    res.cur_fun = None
    res.scope = None


@monkeypatch(Program)
def resolve(self: Program, res: Resolver):
    for topdecl in self.topdecls:
        topdecl.resolve(res)

    if "main" not in res.functions:
        raise ResolverError("función 'main' no presente")

    if res.functions["main"].typ != TypeFun(params=[], ret=TypeInt):
        raise ResolverError(
            "función 'main' debe de devolver un entero y no tener parámetros"
        )
