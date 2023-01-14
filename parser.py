# fmt: off
from sly import Lexer, Parser
from sly.lex import Token
from astnodes import *
from typenodes import *
# fmt: on


class CLexer(Lexer):
    tokens = {
        NUM,
        NUM_LIT,
        ID,
        STR,
        OR,
        AND,
        EQ_EQ,
        NOT_EQ,
        GREATER_EQ,
        LESSER_EQ,
        SHIFT_L,
        SHIFT_R,
        PLUS_EQ,
        MINUS_EQ,
        STAR_EQ,
        SLASH_EQ,
        SHIFTL_EQ,
        SHIFTR_EQ,
        LOGAND_EQ,
        LOGOR_EQ,
        XOR_EQ,
        KW_INT,
        KW_VOID,
        KW_RETURN,
        KW_IF,
        KW_ELSE,
        KW_WHILE,
        KW_FOR,
        KW_STATIC,
        KW_BREAK,
        KW_CONTINUE,
        KW_SIZEOF,
    }

    # fmt: off
    literals = {
        "(", ")", "=", ";", ",", ">", "<", "+", "-",
        "*", "/", "{", "}", "!", "[", "]", "&",
        "|", "^", "~", "%",
    }
    # fmt: on

    ignore = " \t"
    ignore_comment = "//[^\n]*"

    @_(r"\n+")
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    @_(r"\d+")
    def NUM(self, t):
        t.value = int(t.value)
        return t

    @_("0x[0-9a-fA-F]+", "0b[0-1]+")
    def NUM_LIT(self, t):
        if t.value.startswith("0x"):
            t.value = int(t.value, 16)
        else:
            t.value = int(t.value, 2)
        return t

    ID = r"[a-zA-Z_][a-zA-Z0-9_]*"
    ID[r"int"] = KW_INT
    ID[r"void"] = KW_VOID
    ID[r"return"] = KW_RETURN
    ID[r"if"] = KW_IF
    ID[r"else"] = KW_ELSE
    ID[r"while"] = KW_WHILE
    ID[r"for"] = KW_FOR
    ID[r"static"] = KW_STATIC
    ID[r"break"] = KW_BREAK
    ID[r"continue"] = KW_CONTINUE
    ID[r"sizeof"] = KW_SIZEOF
    STR = r'"([^"]|\\")*"'

    EQ_EQ = r"=="
    OR = r"\|\|"
    AND = r"&&"
    NOT_EQ = r"!="
    GREATER_EQ = r">="
    LESSER_EQ = r"<="
    SHIFT_L = r"<<"
    SHIFT_R = r">>"

    PLUS_EQ = r"+="
    MINUS_EQ = r"-="
    STAR_EQ = r"*="
    SLASH_EQ = r"/="
    SHIFTL_EQ = r"<<="
    SHIFTR_EQ = r">>="
    LOGAND_EQ = r"&="
    LOGOR_EQ = r"|="
    XOR_EQ = r"^="

    def error(self, t):
        tkn = Token()
        tkn.value = t.value[0]
        tkn.lineno = self.lineno
        raise ParserError(tkn)


class ParserError(Exception):
    ...


class CParser(Parser):
    tokens = CLexer.tokens

    # debugfile = "debug.log"

    def error(self, tkn):
        raise ParserError(tkn)

    # --- Top Level --- #

    @_(r"S_")
    def S(self, p):
        return Program(pos=1, topdecls=p[0])

    @_(r"S_ toplevel_stmt")
    def S_(self, p):
        p[0].append(p[1])
        return p[0]

    @_(r"")
    def S_(self, _):
        return []

    @_(r"fun_decl", r"fun_def", r"global_var")
    def toplevel_stmt(self, p):
        return p[0]

    # --- Global Declarations --- #

    @_(r'type var_decl_ ";"')
    def global_var(self, p):
        typ, pos = p[0]
        return VarTop(
            pos=pos,
            typ=typ,
            vars=p[1],
        )

    # --- Function Bodies --- #

    @_('fun "{" body "}"')
    def fun_def(self, p):
        return FunDefTop(
            pos=p[0].pos,
            head=p[0],
            body=p[2],
        )

    @_('fun ";"')
    def fun_decl(self, p):
        return p[0]

    # --- Function Head --- #

    @_('type decl_ptrs ID "(" fun_args ")"')
    def fun(self, p):
        tret, lineno = p[0]
        tret = tret.pointify(p[1])

        name = p[2]

        if len(p[4]) == 0:
            types = []
            params = []
        else:
            types, nptrs, params = zip(*p[4])
            types = [typ[0].pointify(nptr) for typ, nptr in zip(types, nptrs)]

        return FunDeclTop(
            pos=lineno,
            name=name,
            sig=TypeFun(params=types, ret=tret),
            params=params,
        )

    @_("fun_args_")
    def fun_args(self, p):
        return p[0]

    @_("")
    def fun_args(self, p):
        return []

    @_('fun_args_ "," type decl_ptrs ID')
    def fun_args_(self, p):
        p[0].append((p[2], p[3], p[4]))
        return p[0]

    @_("type decl_ptrs ID")
    def fun_args_(self, p):
        return [(p[0], p[1], p[2])]

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
        r"return_stmt",
        r"if_stmt",
        r"block_stmt",
        r"while_stmt",
        r"break_stmt",
        r"continue_stmt",
        r"for_stmt",
    )
    def stmt(self, p):
        return p[0]

    # --- While + Break + Continue Statements --- #

    @_(r'KW_WHILE "(" exp ")" block_stmt')
    def while_stmt(self, p):
        return WhileStmt(pos=p.lineno, cond=p[2], block=p[4])

    @_(r'KW_BREAK ";"')
    def break_stmt(self, p):
        return BreakStmt(pos=p.lineno)

    @_(r'KW_CONTINUE ";"')
    def continue_stmt(self, p):
        return ContinueStmt(pos=p.lineno)

    # --- For Loops --- #

    @_(r'KW_FOR "(" for_decl for_cond for_exp ")" block_stmt')
    def for_stmt(self, p):
        decl = p[2]
        cond = p[3] or NumExp(pos=1, lit=1)
        exp = p[4]
        body = p[6]

        if exp is not None:
            body.stmts.append(exp)

        ret = WhileStmt(pos=p.lineno, cond=cond, block=body)
        if decl is not None:
            ret = BlockStmt(pos=p.lineno, stmts=[decl, ret])

        return ret

    @_(r"stmt", '";"')
    def for_decl(self, p):
        if p[0] == ";":
            return None
        else:
            return p[0]

    @_(r'exp ";"', '";"')
    def for_cond(self, p):
        if p[0] == ";":
            return None
        else:
            return p[0]

    @_(r"exp", "")
    def for_exp(self, p):
        return len(p) == 1 and p[0] or None

    # --- If Statement --- #

    @_(r'KW_IF "(" exp ")" block_stmt else_stmt')
    def if_stmt(self, p):
        return IfStmt(pos=p.lineno, cond=p[2], then=p[4], else_=p[5])

    @_("KW_ELSE block_stmt", "KW_ELSE if_stmt")
    def else_stmt(self, p):
        return p[1]

    @_("")
    def else_stmt(self, p):
        return None

    # --- Expr. Statement --- #

    @_(r'exp ";"')
    def exp_stmt(self, p):
        return ExpStmt(pos=p[0].pos, exp=p[0])

    # --- Return Statement --- #

    @_(r'KW_RETURN ";"')
    def return_stmt(self, _):
        return ReturnStmt(pos=p.lineno, exp=None)

    @_(r'KW_RETURN exp ";"')
    def return_stmt(self, p):
        return ReturnStmt(pos=p.lineno, exp=p[1])

    # --- Block Statement --- #

    @_(r'"{" body "}"')
    def block_stmt(self, p):
        return BlockStmt(pos=p.lineno, stmts=p[1])

    # --- Decl. Variables --- #

    @_(r'is_static type var_decl_ ";"')
    def var_decl(self, p):
        typ, pos = p[1]
        return VarStmt(pos=pos, typ=typ, vars=p[2], is_static=p[0])

    @_(r"KW_STATIC")
    def is_static(self, p):
        return True

    @_(r"")
    def is_static(self, p):
        return False

    @_(r'var_decl_ "," param_decl')
    def var_decl_(self, p):
        p[0].append(p[2])
        return p[0]

    @_(r"param_decl")
    def var_decl_(self, p):
        return [p[0]]

    @_(r"decl_ptrs ID array_idxs var_decl_exp")
    def param_decl(self, p):
        return VarDecl(
            pos=p.lineno,
            name=p[1],
            num_nested_ptr=p[0],
            size_arrays=p[2],
            exp=p[3],
        )

    @_(r'decl_ptrs "*"')
    def decl_ptrs(self, p):
        return p[0] + 1

    @_(r"")
    def decl_ptrs(self, _):
        return 0

    @_(r"")
    def var_decl_exp(self, p):
        return None

    @_(r'"[" NUM "]" array_idxs')
    def array_idxs(self, p):
        if p[1] == 0:
            tkn = Token()
            tkn.value = f"[{p[1]}]"
            tkn.lineno = self.lineno
            raise ParserError(tkn)

        p[3].append(p[1])
        return p[3]

    @_(r"")
    def array_idxs(self, p):
        return []

    @_(r'"=" array', '"=" exp')
    def var_decl_exp(self, p):
        return p[1]

    # --- Vector Initialization --- #

    @_(r'"{" array_rec "}"', r'"{" array_base "}"')
    def array(self, p):
        return ArrayExp(pos=p.lineno, exps=p[1])

    @_(r'array_rec "," array')
    def array_rec(self, p):
        p[0].append(p[2])
        return p[0]

    @_(r"array")
    def array_rec(self, p):
        return [p[0]]

    @_(r'array_base "," exp')
    def array_base(self, p):
        p[0].append(p[2])
        return p[0]

    @_(r"exp")
    def array_base(self, p):
        return [p[0]]

    # --- Expression --- #

    @_(r"assign")
    def exp(self, p):
        return p[0]

    # --- Assignment --- #

    @_(
        'unary "=" assign',
        "unary PLUS_EQ assign",
        "unary MINUS_EQ assign",
        "unary STAR_EQ assign",
        "unary SLASH_EQ assign",
        "unary SHIFTL_EQ assign",
        "unary SHIFTR_EQ assign",
        "unary LOGAND_EQ assign",
        "unary LOGOR_EQ assign",
        "unary XOR_EQ assign",
    )
    def assign(self, p):
        lval = p[0]
        if p[1] != "=":
            rval = BinaryExp(
                pos=p.lineno,
                exp1=VarExp(pos=p.lineno),
                op=p[1][:-1],
                exp2=p[2],
            )
        else:
            rval = p[2]

        return AssignExp(pos=p[0].pos, var=lval, exp=rval)

    @_("or_exp")
    def assign(self, p):
        return p[0]

    # --- || --- #

    @_("or_exp OR and_exp")
    def or_exp(self, p):
        return BinaryExp(pos=p[0].pos, exp1=p[0], op="||", exp2=p[2])

    @_("and_exp")
    def or_exp(self, p):
        return p[0]

    # --- && --- #

    @_("and_exp AND or_bin")
    def and_exp(self, p):
        return BinaryExp(pos=p[0].pos, exp1=p[0], op="&&", exp2=p[2])

    @_("or_bin")
    def and_exp(self, p):
        return p[0]

    # --- | --- #

    @_(r'or_bin "|" xor_bin')
    def or_bin(self, p):
        return BinaryExp(pos=p[0].pos, exp1=p[0], op="|", exp2=p[2])

    @_(r"xor_bin")
    def or_bin(self, p):
        return p[0]

    # --- ^ --- #

    @_(r'xor_bin "^" and_bin')
    def xor_bin(self, p):
        return BinaryExp(pos=p[0].pos, exp1=p[0], op="^", exp2=p[2])

    @_(r"and_bin")
    def xor_bin(self, p):
        return p[0]

    # --- & --- #

    @_(r'and_bin "&" comp_exp')
    def and_bin(self, p):
        return BinaryExp(pos=p[0].pos, exp1=p[0], op="&", exp2=p[2])

    @_(r"comp_exp")
    def and_bin(self, p):
        return p[0]

    # --- Comparison --- #

    @_(
        "comp_exp EQ_EQ shiftop",
        "comp_exp NOT_EQ shiftop",
        "comp_exp LESSER_EQ shiftop",
        "comp_exp GREATER_EQ shiftop",
        'comp_exp ">" shiftop',
        'comp_exp "<" shiftop',
    )
    def comp_exp(self, p):
        return BinaryExp(pos=p[0].pos, exp1=p[0], op=p[1], exp2=p[2])

    @_("shiftop")
    def comp_exp(self, p):
        return p[0]

    # --- Lshift/Rshift --- #

    @_(r"shiftop SHIFT_R sum", r"shiftop SHIFT_L sum")
    def shiftop(self, p):
        return BinaryExp(pos=p[0].pos, exp1=p[0], op=p[1], exp2=p[2])

    @_("sum")
    def shiftop(self, p):
        return p[0]

    # --- Summands --- #

    @_('sum "+" prod', 'sum "-" prod')
    def sum(self, p):
        return BinaryExp(pos=p[0].pos, exp1=p[0], op=p[1], exp2=p[2])

    @_("prod")
    def sum(self, p):
        return p[0]

    # --- Product --- #

    @_('prod "*" unary', 'prod "/" unary', 'prod "%" unary')
    def prod(self, p):
        return BinaryExp(pos=p[0].pos, exp1=p[0], op=p[1], exp2=p[2])

    @_("unary")
    def prod(self, p):
        return p[0]

    # --- Unary --- #

    @_(
        '"!" unary',
        '"-" unary',
        '"*" unary',
        '"&" unary',
        '"~" unary',
    )
    def unary(self, p):
        return UnaryExp(pos=p.lineno, op=p[0], exp=p[1])

    @_(r'"(" type_lit ")" unary')
    def unary(self, p):
        return CastExp(pos=p.lineno, to=p[1], exp=p[3])

    @_("call")
    def unary(self, p):
        return p[0]

    # --- Call/Index --- #

    @_(r'ID "(" call_args ")"')
    def call(self, p):
        return CallExp(
            pos=p.lineno,
            callee=VarExp(pos=p.lineno, lit=p[0], resolved_as=None),
            args=p[2],
        )

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
        return UnaryExp(
            pos=p[0].pos,
            op="*",
            exp=BinaryExp(pos=p[0].pos, exp1=p[0], op="+", exp2=p[2]),
        )

    @_(r"atom")
    def call(self, p):
        return p[0]

    # --- Atoms --- #

    @_('"(" exp ")"')
    def atom(self, p):
        return p[1]

    @_(
        'KW_SIZEOF "(" exp ")"',
        'KW_SIZEOF "(" type_lit ")"',
    )
    def atom(self, p):
        return SizeofExp(pos=p.lineno, type=p[2])

    @_("ID")
    def atom(self, p):
        return VarExp(pos=p.lineno, lit=p[0], resolved_as=None)

    @_("NUM")
    def atom(self, p):
        return NumExp(pos=p.lineno, lit=p[0])

    @_("NUM_LIT")
    def atom(self, p):
        return NumExp(pos=p.lineno, lit=p[0])

    @_("STR")
    def atom(self, p):
        return StrExp(pos=p.lineno, lit=p[0])

    # --- Type "Literal" --- #

    @_('type_lit "[" NUM "]"')
    def type_lit(self, p):
        if p[2] == 0:
            tkn = Token()
            tkn.value = f"[{p[2]}]"
            tkn.lineno = self.lineno
            raise ParserError(tkn)

        return p[0].as_array(p[2])

    @_("type_lit_ptr")
    def type_lit(self, p):
        return p[0]

    @_('type_lit_ptr "*"')
    def type_lit_ptr(self, p):
        return p[0].as_ptr()

    @_("type")
    def type_lit_ptr(self, p):
        return p[0][0]

    # --- Types --- #

    @_(r"KW_INT")
    def type(self, p):
        return TypeInt, p.lineno

    @_(r"KW_VOID")
    def type(self, p):
        return TypeVoid, p.lineno
