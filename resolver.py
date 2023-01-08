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
    cur_fun: Fun = None
    scope: Scope = None
    globals: dict[str, Union[Fun, Global]] = field(default_factory=dict)

    def resolve(self, ast: Ast) -> Type:
        ast.resolve(self)
        return self

    def add_local(self, name: str, typ: Type) -> Local:
        if self.cur_fun is None:
            raise Exception("no se puede usar 'add_local' en contexto global")

        if name in self.scope.variables:
            raise ResolverError(f"variable '{name}' ya presente en el ámbito actual")

        local = self.scope.add_local(name, typ)
        self.cur_fun.max_stack_size = max(self.scope.top, self.cur_fun.max_stack_size)
        return local

    def find_var(self, name: str) -> Union[Local, Global, None]:
        var = self.scope is not None and self.scope.find(name) or None
        return var or self.globals.get(name, None)

    def is_declared_in_scope(self, name: str) -> bool:
        if self.scope is None:
            # return name in self.globals <= TODO
            return False
        else:
            return name in self.scope.variables

    def open_scope(self):
        new_scope = Scope(top=self.scope.top)
        new_scope.prev, self.scope = self.scope, new_scope

    def close_scope(self):
        self.scope = self.scope.prev


class ResolverError(Exception):
    ...


# --- Expressions --- #


@monkeypatch(NumExp)
def resolve(self, _):
    return TypeInt


@monkeypatch(StrExp)
def resolve(self, _):
    return TypePtr(inner=TypeChar)


@monkeypatch(ArrayExp)
def resolve(self: ArrayExp, res: Resolver):
    texps = [exp.resolve(res) for exp in self.exps]

    if not all(a == b for a, b in zip(texps, texps[1:])):
        raise ResolverError("elementos del vector literal no tienen los mismos tipos")

    return TypeArray(inner=texps[0], size=len(texps))


@monkeypatch(VarExp)
def resolve(self: VarExp, res: Resolver):
    var = res.find_var(self.lit)

    if var is None:
        raise ResolverError(f"variable '{self.lit}' no declarada")

    if isinstance(var, Fun):
        raise ResolverError(f"no se puede usar la función '{self.lit}' como variable")

    self.resolved_as = var
    return var.typ.dup_as_lvalue()


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
        return t.inner.dup_as_lvalue()

    if self.op in {"-", "!"}:
        if t != TypeInt:
            raise ResolverError(
                f"se espera un entero para el operador unario {self.op}, pero se encontró {t}"
            )
        return t.dup_as_rvalue()


@monkeypatch(BinaryExp)
def resolve(self: BinaryExp, res: Resolver):
    t1 = self.exp1.resolve(res)
    t2 = self.exp2.resolve(res)

    if self.op in {"*", "/", "||", "&&"}:
        if t1 != TypeInt or t2 != TypeInt:
            raise ResolverError(
                f"se esperan tipos enteros para el operador {self.op}, pero se obtuvo {t1} y {t2}"
            )
        return t1.dup_as_rvalue()

    if self.op in {"==", "!=", "<=", ">=", "<", ">"}:
        if t1 != t2:
            raise ResolverError(f"no se pueden comparar tipos {t1} y {t2}")
        return TypeInt.dup_as_rvalue()

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
                    exp1=self.exp1, exp2=NumExp(t.inner.sizeof()), op="*"
                )

            return t.dup_as_rvalue()

        else:
            return TypeInt.dup_as_rvalue()


@monkeypatch(CallExp)
def resolve(self: CallExp, res: Resolver):
    fun = res.find_var(self.callee)
    if isinstance(fun, Local) or isinstance(fun, Global):
        raise ResolverError(
            f"función llamada '{self.callee}' es una variable, no una función"
        )

    if fun is None:
        raise ResolverError(f"función '{self.callee}' no encontrada")

    for tparam, arg in zip(fun.typ.params, self.args):
        targ = arg.resolve(res)

        if targ != tparam:
            raise ResolverError(
                f"función tomó argumento de tipo {targ}, pero se necesita tipo {tparam}"
            )

    self.resolved_as = fun
    return fun.typ.ret.dup_as_rvalue()


@monkeypatch(AssignExp)
def resolve(self: AssignExp, res: Resolver):
    tassign = self.var.resolve(res)
    tval = self.exp.resolve(res)

    if tassign.is_rvalue():
        raise ResolverError("valor al que se asigna no es un lvalor")

    if isinstance(tassign, TypeArray):
        raise ResolverError("valor al que se asigna no puede ser un vector")

    if tval != tassign:
        raise ResolverError(
            f"valor al que se asigna ({tassign}) no tiene el mismo tipo que la expresión {tval}"
        )

    return tval.dup_as_rvalue()


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
            if typ != texp:
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
    self.cond.resolve(res)
    # trivialmente asumimos que cualquier valor se convierte a booleano

    self.then.resolve(res)

    if self.else_ is not None:
        self.else_.resolve(res)


@monkeypatch(WhileStmt)
def resolve(self: WhileStmt, res: Resolver):
    tcond = self.cond.resolve(res)
    # trivialmente asumimos que cualquier valor se convierte a booleano

    self.block.resolve(res)


# --- Top Level --- #


@monkeypatch(FunDeclTop)
def resolve(self: FunDeclTop, res: Resolver):
    if self.name in res.globals:
        problem = isinstance(res.globals[self.name], Fun) and "función" or "variable global"
        raise ResolverError(f"{problem} '{self.name}' ya declarada")

    res.globals[self.name] = Fun(name=self.name, typ=self.sig, params=self.params)


@monkeypatch(VarTop)
def resolve(self: VarTop, res: Resolver):
    t = self.typ
    if t == TypeVoid:
        raise ResolverError(f"no pueden existir variables tipo void")

    for var in self.vars:
        if var.lit in res.globals:
            raise ResolverError(f"variable global '{var.lit}' ya definida")

        var.resolved_as = Global(typ=t, name=var.lit)
        res.globals[var.lit] = var.resolved_as


@monkeypatch(FunDefTop)
def resolve(self: FunDefTop, res: Resolver):
    name = self.head.name

    fun = res.globals.get(name, None)
    if fun is not None:
        if isinstance(fun, Global):
            raise ResolverError(f"variable global '{name}' ya declarada")

        if fun.initialized:
            raise ResolverError(f"función '{name}' ya definida")

        fun.params = self.head.params
        if fun.typ != self.head.sig:
            raise ResolverError(
                f"tipo de la definición de la función '{name}' no es la misma que la de su declaración"
            )
    else:
        self.head.resolve(res)

    fun: Fun = res.globals[name]
    res.cur_fun = fun
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

    main = res.globals.get("main", None)

    if main is None:
        raise ResolverError("función 'main' no presente")

    if main.typ != TypeFun(params=[], ret=TypeInt):
        raise ResolverError(
            "función 'main' debe de devolver un entero y no tener parámetros"
        )
