from dataclasses import dataclass, field
from typenodes import *
from astnodes import *
from typing import Tuple, Optional, Union


@dataclass
class TopObject:
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
    initialized: bool = False


@dataclass
class NativeFun(TopObject):
    name: str = ""
    callback: "None" = None


def _printf_resolve(self, res):
    if len(self.args) == 0 or not isinstance(self.args[0], StrExp):
        res.throw(self, "primer argumento de printf tiene que ser una cadena literal")

    fmt: str = self.args[0].lit
    num_formats = fmt.count("%i")

    if len(self.args) != 1 + num_formats:
        res.throw(
            self,
            f"número de argumentos admitido por esta llamada de printf tiene que ser {1 + num_formats}, no {len(self.args)}",
        )

    res.resolve_exp(self.args[0])
    rest_tparams = []
    for i, arg in zip(range(1, num_formats + 1), self.args[1:]):
        targ = arg.resolve(res)
        tparam = TypeInt

        if targ != tparam:
            res.throw(
                self,
                f"función tomó argumento de tipo {targ}, pero se necesita tipo {tparam}",
            )
        rest_tparams.append(tparam)

    self.callee.resolved_as = Fun(
        typ=TypeFun(params=[TypeChar.as_ptr(), *rest_tparams], ret=TypeVoid),
        name="printf",
        initialized=True,
    )
    return TypeVoid


def _scanf_resolve(self, res):
    if len(self.args) == 0 or not isinstance(self.args[0], StrExp):
        res.throw(self, "primer argumento de scanf tiene que ser una cadena literal")

    fmt: str = self.args[0].lit
    num_formats = fmt.count("%i")

    if len(self.args) != 1 + num_formats:
        res.throw(
            self,
            f"número de argumentos admitido por esta llamada de printf tiene que ser {1 + num_formats}, no {len(self.args)}",
        )

    res.resolve_exp(self.args[0])
    rest_tparams = []
    for i, arg in zip(range(1, num_formats + 1), self.args[1:]):
        targ = arg.resolve(res)
        tparam = TypeInt.as_ptr()

        if targ != tparam:
            res.throw(
                self,
                f"función tomó argumento de tipo {targ}, pero se necesita tipo {tparam}",
            )
        rest_tparams.append(tparam)

    self.callee.resolved_as = Fun(
        typ=TypeFun(params=[TypeChar.as_ptr(), *rest_tparams], ret=TypeInt),
        name="scanf",
        initialized=True,
    )
    return TypeInt


native_functions = {
    "printf": NativeFun(
        name="printf",
        callback=_printf_resolve,
    ),
    "scanf": NativeFun(
        name="printf",
        callback=_scanf_resolve,
    ),
    "malloc": Fun(
        name="malloc",
        initialized=True,
        typ=TypeFun(params=[TypeInt], ret=TypeVoid.as_ptr()),
    ),
    "calloc": Fun(
        name="calloc",
        initialized=True,
        typ=TypeFun(params=[TypeInt, TypeInt], ret=TypeVoid),
    ),
    "realloc": Fun(
        name="realloc",
        initialized=True,
        typ=TypeFun(params=[TypeVoid.as_ptr(), TypeInt], ret=TypeVoid.as_ptr()),
    ),
    "free": Fun(
        name="free",
        initialized=True,
        typ=TypeFun(params=[TypeVoid.as_ptr()], ret=TypeVoid),
    ),
}
