# fmt: off
from sly import Lexer, Parser
from astnodes import *
from typenodes import *
# fmt: on


class CLexer(Lexer):
    tokens = {
        NUM,
        OR,
        AND,
        EQ_EQ,
        NOT_EQ,
        GREATER_EQ,
        LESSER_EQ,
        ID,
        STR,
        KW_INT,
        KW_VOID,
        KW_PRINTF,
        KW_RETURN,
        KW_SCANF,
    }

    # fmt: off
    literals = {
        "(", ")", "=", ";", ",", ">", "<", "+", "-",
        "*", "/", "{", "}", "!", "&", "[", "]",
    }
    # fmt: on

    ignore = " \t"

    @_(r"\n+")
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    @_(r"[0-9]+")
    def NUM(self, t):
        t.value = int(t.value)
        return t

    ID = r"[a-zA-Z_][a-zA-Z0-9_]*"
    ID[r"int"] = KW_INT
    ID[r"void"] = KW_VOID
    ID[r"printf"] = KW_PRINTF
    ID[r"return"] = KW_RETURN
    ID[r"scanf"] = KW_SCANF
    STR = r'"([^"]|\\")*"'

    EQ_EQ = r"=="
    OR = r"\|\|"
    AND = r"&&"
    NOT_EQ = r"!="
    GREATER_EQ = r">="
    LESSER_EQ = r"<="


class ParserError(Exception):
    ...


class CParser(Parser):
    tokens = CLexer.tokens

    def error(self, tkn):
        raise ParserError(tkn)

    # --- Top Level --- #

    @_(r"S_")
    def S(self, p):
        return Program(p[0])

    @_(r"S_ toplevel_stmt")
    def S_(self, p):
        p[0].append(p[1])
        return p[0]

    @_(r"")
    def S_(self, _):
        return []

    @_(r"fun_decl", r"fun_def")
    def toplevel_stmt(self, p):
        return p[0]

    # --- Functions --- #

    @_('fun "{" body "}"')
    def fun_def(self, p):
        return FunDefTop(p[0], p[2])

    @_('fun ";"')
    def fun_decl(self, p):
        return p[0]

    @_('type funptr ID "(" fun_args ")"')
    def fun(self, p):
        types, params = p[4]
        tret = p[0]
        for _ in range(p[1]):
            tret = TypePtr(inner=tret)

        return FunDeclTop(name=p[2], sig=TypeFun(params=types, ret=tret), params=params)

    @_(r'funptr "*"')
    def funptr(self, p):
        return p[0] + 1

    @_(r'')
    def funptr(self, _):
        return 0

    @_("fun_args_")
    def fun_args(self, p):
        return p[0]

    @_("")
    def fun_args(self, p):
        return ([], [])

    @_('fun_args_ "," type lvar')
    def fun_args_(self, p):
        params = p[0]
        name, typf = p[3]
        params[0].append(typf(p[2]))
        params[1].append(name.lit)
        return params

    @_("type lvar")
    def fun_args_(self, p):
        name, typf = p[1]
        return ([typf(p[0])], [name.lit])

    # --- Statements --- #

    @_(r"body stmt")
    def body(self, p):
        p[0].append(p[1])
        return p[0]

    @_(r"")
    def body(self, p):
        return []

    @_(
        r"exp_stmt",
        r"var_decl",
        r"printf_stmt",
        r"scanf_stmt",
        r"return_stmt",
    )
    def stmt(self, p):
        return p[0]

    @_(r'exp ";"')
    def exp_stmt(self, p):
        return ExpStmt(p[0])

    @_('KW_PRINTF "(" STR printf_args ")" ";"')
    def printf_stmt(self, p):
        return PrintfStmt(p[2], p[3])

    @_('printf_args "," exp')
    def printf_args(self, p):
        p[0].append(p[2])
        return p[0]

    @_("")
    def printf_args(self, p):
        return []

    @_(r'KW_RETURN ";"')
    def return_stmt(self, _):
        return ReturnStmt(None)

    @_(r'KW_RETURN exp ";"')
    def return_stmt(self, p):
        return ReturnStmt(p[1])

    @_('KW_SCANF "(" STR scanf_args ")" ";"')
    def scanf_stmt(self, p):
        return ScanfStmt(p[2], p[3])

    @_('scanf_args "," exp')
    def scanf_args(self, p):
        p[0].append(p[2])  # list of arguments
        return p[0]

    @_("")
    def scanf_args(self, p):
        return []

    # --- Decl. Variables --- #

    @_(r'type var_decl_ ";"')
    def var_decl(self, p):
        vars, _ = p[1]
        return VarStmt(vars)

    @_(r'var_decl_ "," param_decl')
    def var_decl_(self, p):
        typf, name, exp = p[2]
        vars, typ = p[0]
        vars.append((typf(typ), name, exp))
        return vars, typ

    @_(r"param_decl")
    def var_decl_(self, p):
        typ = p[-2]
        typf, name, exp = p[0]
        return [(typf(typ), name, exp)], typ

    @_(r"lvar var_decl_exp")
    def param_decl(self, p):
        name, typf = p[0]
        return typf, name, p[1]

    @_(r'"=" exp')
    def var_decl_exp(self, p):
        return p[1]

    @_(r"")
    def var_decl_exp(self, p):
        return None

    @_(r'lvar "[" NUM "]"')
    def lvar(self, p):
        name, typf = p[0]
        size = p[2]
        return name, lambda typ: TypeArray(inner=typf(typ), size=size)

    @_(r"lvar_ptr")
    def lvar(self, p):
        return p[0]

    @_(r'"*" lvar_ptr')
    def lvar_ptr(self, p):
        name, typf = p[1]
        return name, lambda typ: TypePtr(inner=typf(typ))

    @_(r"lvar_atom")
    def lvar_ptr(self, p):
        return p[0]

    @_(r"ID")
    def lvar_atom(self, p):
        return VarExp(p[0]), lambda typ: typ

    @_(r'"(" lvar ")"')
    def lvar_atom(self, p):
        return p[1]

    # --- Expresiones --- #

    @_(r"assign")
    def exp(self, p):
        return p[0]

    # Asignaciones

    @_('unary "=" assign')
    def assign(self, p):
        return AssignExp(p[0], p[2])

    @_("or_exp")
    def assign(self, p):
        return p[0]

    # ||

    @_("or_exp OR and_exp")
    def or_exp(self, p):
        return BinaryExp(p[0], "||", p[2])

    @_("and_exp")
    def or_exp(self, p):
        return p[0]

    # &&

    @_("and_exp AND comp_exp")
    def and_exp(self, p):
        return BinaryExp(p[0], "&&", p[2])

    @_("comp_exp")
    def and_exp(self, p):
        return p[0]

    # COMPARISON

    @_(
        "sum EQ_EQ comp_exp",
        "sum NOT_EQ comp_exp",
        "sum LESSER_EQ comp_exp",
        "sum GREATER_EQ comp_exp",
        'sum ">" comp_exp',
        'sum "<" comp_exp',
    )
    def comp_exp(self, p):
        return BinaryExp(p[0], p[1], p[2])

    @_("sum")
    def comp_exp(self, p):
        return p[0]

    # SUM

    @_('sum "+" prod', 'sum "-" prod')
    def sum(self, p):
        return BinaryExp(p[0], p[1], p[2])

    @_("prod")
    def sum(self, p):
        return p[0]

    # PRODUCT

    @_('prod "*" unary', 'prod "/" unary')
    def prod(self, p):
        return BinaryExp(p[0], p[1], p[2])

    @_("unary")
    def prod(self, p):
        return p[0]

    # UNARY

    @_(
        '"!" unary',
        '"-" unary',
        '"*" unary',
        '"&" unary',
    )
    def unary(self, p):
        return UnaryExp(p[0], p[1])

    @_("call")
    def unary(self, p):
        return p[0]

    # CALL

    @_(r'call "(" call_args ")"')
    def call(self, p):
        return CallExp(p[0], p[2])

    @_(r"")
    def call_args(self, _):
        return []

    @_(r"call_args_")
    def call_args(self, p):
        return p[0]

    @_(r'call_args_ "," exp')
    def call_args_(self, p):
        p[0].append(p[2])
        return p[0]

    @_(r"exp")
    def call_args_(self, p):
        return [p[0]]

    @_(r'call "[" exp "]"')
    def call(self, p):
        return UnaryExp(op="*", exp=BinaryExp(exp1=p[0], op="+", exp2=p[2]))

    @_(r"atom")
    def call(self, p):
        return p[0]

    # ATOM

    @_('"(" exp ")"')
    def atom(self, p):
        return p[1]

    @_("ID")
    def atom(self, p):
        return VarExp(lit=p[0], resolved_as=None)

    @_("NUM")
    def atom(self, p):
        return NumExp(p[0])

    # --- Tipos --- #

    @_(r"KW_INT")
    def type(self, p):
        return TypeInt

    @_(r"KW_VOID")
    def type(self, p):
        return TypeVoid
