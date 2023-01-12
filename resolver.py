from astnodes import *
from typenodes import *
from commonitems import *
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

    def add_local(self, res: "Resolver", name: str, typ: Type, is_static: bool = False):
        if is_static:
            local = Global(
                typ=typ,
                name=name + SYM + res.cur_fun.head.name + SYM + str(res.static_var_count),
            )
            res.static_var_count += 1
        else:
            self.top += typ.sizeof()
            local = Local(
                addr=self.top,
                typ=typ,
            )
        self.variables[name] = local
        return local


class ResolverError(Exception):
    ...


SYM = "."


@dataclass
class Resolver:
    cur_fun: FunDefTop = None
    scope: Scope = None
    globals: dict[str, Union[Fun, Global]] = field(default_factory=dict)
    error_state: bool = False
    static_var_count: int = 0
    nested_loops: int = 0

    def error(self, ast: Ast, msg: str) -> None:
        self.error_state = True
        print(f"error:{ast.pos}: {msg}")

    def throw(self, ast: Ast, msg: str) -> None:
        self.error(ast, msg)
        raise ResolverError()

    def resolve(self, ast: Ast) -> "Resolver":
        ast.resolve(self)
        return self

    def resolve_exp(self, ast: Ast) -> Union[Type, None]:
        try:
            return ast.resolve(self)
        except ResolverError:
            return None

    def add_local(self, name: str, typ: Type, is_static: bool = False) -> Local:
        if self.cur_fun is None:
            raise Exception("no se puede usar 'add_local' en contexto global")

        local = self.scope.add_local(self, name, typ, is_static=is_static)

        if not is_static:
            self.cur_fun.max_stack_size = max(
                self.scope.top, self.cur_fun.max_stack_size
            )

        return local

    def find_var(self, name: str) -> Union[Local, Global, None]:
        var = self.scope is not None and self.scope.find(name) or None
        return var or self.globals.get(name, None)

    def is_declared_in_scope(self, name: str) -> bool:
        if self.scope is None:
            return name in self.globals
        else:
            return name in self.scope.variables

    def open_scope(self):
        new_scope = Scope(top=self.scope.top)
        new_scope.prev, self.scope = self.scope, new_scope

    def close_scope(self):
        self.scope = self.scope.prev


# --- Expressions --- #


@monkeypatch(NumExp)
def resolve(self: NumExp, res: Resolver):
    if isinstance(self.lit, float):
        return TypeFloat
    else:
        return TypeInt


@monkeypatch(StrExp)
def resolve(self, _):
    return TypePtr(inner=TypeChar)


@monkeypatch(ArrayExp)
def resolve(self: ArrayExp, res: Resolver):
    texps = [exp.resolve(res) for exp in self.exps]

    if not all(a == b for a, b in zip(texps, texps[1:])):
        res.throw(self, "elementos del vector literal no tienen los mismos tipos")

    return TypeArray(inner=texps[0], size=len(texps))


@monkeypatch(VarExp)
def resolve(self: VarExp, res: Resolver):
    var = res.find_var(self.lit)
    if var is None:
        res.throw(self, f"variable '{self.lit}' no declarada")

    if isinstance(var, Fun):
        res.throw(self, f"no se puede usar la función '{self.lit}' como variable")

    self.resolved_as = var
    return var.typ.dup_as_lvalue()


@monkeypatch(UnaryExp)
def resolve(self: UnaryExp, res: Resolver):
    t = self.exp.resolve(res)

    if self.op == "&":
        if t.is_rvalue():
            res.throw(self, f"se está tomando referencia de un r-valor")
        return TypePtr(lvalue=False, inner=t)

    if self.op == "*":
        if not (isinstance(t, TypePtr) or isinstance(t, TypeArray)):
            res.throw(
                self, f"se está dereferenciando un valor que no es puntero o vector"
            )
        return t.inner.dup_as_lvalue()

    if self.op in {"-", "!", "~"}:
        if t != TypeInt:
            res.throw(
                self,
                f"se espera un entero para el operador unario {self.op}, pero se encontró {t}",
            )
        return t.dup_as_rvalue()


@monkeypatch(BinaryExp)
def resolve(self: BinaryExp, res: Resolver):
    t1 = self.exp1.resolve(res)
    t2 = self.exp2.resolve(res)

    if self.op in {"*", "/", "%", "||", "&&", "|", "&", "^", "<<", ">>"}:
        if t1 != TypeInt or t2 != TypeInt:
            res.throw(
                self,
                f"se esperan tipos enteros para el operador {self.op}, pero se obtuvo {t1} y {t2}",
            )
        return t1.dup_as_rvalue()

    if self.op in {"==", "!=", "<=", ">=", "<", ">"}:
        if t1 != t2:
            res.throw(self, f"no se pueden comparar tipos {t1} y {t2}")
        return TypeInt.dup_as_rvalue()

    if self.op in {"+", "-"}:
        is_ptr_incr = t1.is_ptr() and t2 == TypeInt or t2.is_ptr() and t1 == TypeInt
        is_num_add = t1 == TypeInt and t2 == TypeInt

        if not (is_ptr_incr or is_num_add):
            res.throw(
                self,
                f"se espera puntero y entero o enteros para operador {self.op}, pero se recibió {t1} y {t2}",
            )

        if is_ptr_incr:
            if t1.is_ptr():
                t = t1
                self.exp2 = BinaryExp(
                    pos=self.pos,
                    exp1=self.exp2,
                    exp2=NumExp(pos=self.pos, lit=t.inner.sizeof()),
                    op="*",
                )

            else:
                t = t2
                self.exp1 = BinaryExp(
                    pos=self.pos,
                    exp1=self.exp1,
                    exp2=NumExp(pos=self.pos, lit=t.inner.sizeof()),
                    op="*",
                )

            return t.dup_as_rvalue()

        else:
            return TypeInt.dup_as_rvalue()


@monkeypatch(CallExp)
def resolve(self: CallExp, res: Resolver):
    name_fun = self.callee.lit
    fun = res.find_var(name_fun)
    if fun is None:
        res.throw(self, f"función '{name_fun}' no encontrada")

    if isinstance(fun, Local) or isinstance(fun, Global):
        res.throw(self, f"función llamada '{name_fun}' es una variable, no una función")

    if isinstance(fun, NativeFun):
        return fun.callback(self, res)

    self.callee.resolved_as = fun
    if isinstance(fun, Fun):
        if not fun.initialized:
            res.throw(self, "llamando a función aún no definida, sólo declarada")

        if len(fun.typ.params) != len(self.args):
            res.throw(
                self,
                f"función toma {len(self.args)} número de argumentos, pero se dieron sólo {len(fun.typ.params)}",
            )

        for tparam, arg in zip(fun.typ.params, self.args):
            targ = arg.resolve(res)

            if targ != tparam:
                res.throw(
                    self,
                    f"función tomó argumento de tipo {targ}, pero se necesita tipo {tparam}",
                )

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


@monkeypatch(SizeofExp)
def resolve(self: SizeofExp, res: Resolver):
    if isinstance(self.type, Ast):
        self.type = res.resolve_exp(self.type)
    return TypeInt


# --- Statements --- #


@monkeypatch(ExpStmt)
def resolve(self, res: Resolver):
    res.resolve_exp(self.exp)


@monkeypatch(ReturnStmt)
def resolve(self, res: Resolver):
    tret = res.cur_fun.head.sig.ret

    if self.exp is not None:
        if tret == TypeVoid:
            raise ResolverError("no se puede devolver valores desde funciones void")

        t = res.resolve_exp(self.exp)
        if t is not None and t != tret:
            res.error(
                self,
                f"se quiere devolver una expresión de tipo {t} en una función que devuelve {tret}",
            )

    elif tret != TypeVoid:
        res.error(self, "se intenta retornar de una función no void sin una expresión")


@monkeypatch(VarStmt)
def resolve(self: VarStmt, res: Resolver):
    tbase = self.typ

    for var in self.vars:
        typ = var.wrap_type(tbase)
        if typ == TypeVoid:
            res.error(var, f"no pueden existir variables tipo void")
            continue

        if var.exp is not None:
            texp = res.resolve_exp(var.exp)
            if texp is None:
                continue

            if typ != texp:
                res.error(
                    var,
                    f"se pretende asignar a variable '{var.name}' con expresión de tipo {texp}, se espera tipo {typ}",
                )
                continue

            if self.is_static and (
                isinstance(typ, TypeArray) or isinstance(texp, TypeArray)
            ):
                res.error(self, f"variable estática no puede ser un vector")
                continue

        if var.name in res.scope.variables:
            res.error(self, f"variable {var.name} ya presente en el ámbito actual")
            continue

        var.resolved_as = res.add_local(var.name, typ, is_static=self.is_static)


@monkeypatch(BlockStmt)
def resolve(self: BlockStmt, res: Resolver):
    res.open_scope()
    for stmt in self.stmts:
        stmt.resolve(res)
    res.close_scope()


@monkeypatch(IfStmt)
def resolve(self: IfStmt, res: Resolver):
    res.resolve_exp(self.cond)
    self.then.resolve(res)
    if self.else_ is not None:
        self.else_.resolve(res)


@monkeypatch(WhileStmt)
def resolve(self: WhileStmt, res: Resolver):
    res.resolve_exp(self.cond)
    res.nested_loops += 1
    self.block.resolve(res)
    res.nested_loops -= 1


@monkeypatch(BreakStmt)
def resolve(self, res: Resolver):
    if res.nested_loops == 0:
        res.error(self, "se intenta hacer un 'break' fuera de un bucle")


@monkeypatch(ContinueStmt)
def resolve(self, res: Resolver):
    if res.nested_loops == 0:
        res.error(self, "se intenta hacer un 'continue' fuera de un bucle")


@monkeypatch(CastExp)
def resolve(self: CastExp, res: Resolver):
    # trivialmente, todo es convertible a todo
    res.resolve_exp(self.exp)
    return self.to


# --- Top Level --- #


@monkeypatch(VarTop)
def resolve(self: VarTop, res: Resolver):
    tbase = self.typ

    for var in self.vars:
        t = var.wrap_type(tbase)
        if t == TypeVoid:
            res.error(var, f"no pueden existir variables tipo void")
            continue

        if isinstance(t, TypeArray):
            res.error(var, f"no se admiten vectores como globales")
            continue

        if var.exp is not None:
            res.error(var, f"no se admite asignar expresiones a globales")
            continue

        if var.name in res.globals:
            res.error(var, f"variable global '{var.name}' ya definida")
            continue

        var.resolved_as = res.globals[var.name] = Global(typ=t, name=var.name)


@monkeypatch(FunDeclTop)
def resolve(self: FunDeclTop, res: Resolver):
    if self.name in res.globals:
        problem = (
            isinstance(res.globals[self.name], Fun) and "función" or "variable global"
        )
        res.throw(self, f"{problem} '{self.name}' ya declarada")
    else:
        res.globals[self.name] = Fun(
            name=self.name,
            typ=self.sig,
            initialized=False,
        )


@monkeypatch(FunDefTop)
def resolve(self: FunDefTop, res: Resolver):
    name = self.head.name
    fun = res.globals.get(name, None)

    if fun is None:
        self.head.resolve(res)
    else:
        if isinstance(fun, Global):
            res.throw(self, f"variable global '{name}' ya declarada")

        if fun.initialized:
            res.throw(self, f"función '{name}' ya definida")

        if fun.typ != self.head.sig:
            res.throw(
                f"tipo de la definición de la función '{name}' no es la misma que la de su declaración"
            )

    res.globals[self.head.name].initialized = True
    res.cur_fun = self

    vars = {}
    off = 8
    for typ, param in zip(self.head.sig.params, self.head.params):
        if param in vars:
            res.error(self, f"parámetro '{param}' ya declarado")
            continue

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
        try:
            topdecl.resolve(res)
        except ResolverError:
            pass

    main = res.globals.get("main", None)

    if main is None:
        res.error(self, "función 'main' no presente")

    if main.typ != TypeFun(params=[], ret=TypeInt):
        res.error(
            self, "función 'main' debe de devolver un entero y no tener parámetros"
        )
