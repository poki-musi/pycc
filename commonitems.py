from dataclasses import dataclass, field
from typenodes import *
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
