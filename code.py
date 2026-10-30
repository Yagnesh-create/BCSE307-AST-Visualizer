#!/usr/bin/env python3
# ============================================================================
# AST VISUALIZER / PRETTY PRINTER  --  Single-file implementation
# Team 16 | Project ID: M13 | BCSE307 Compiler Design | Review 3 (Final Completion)
# ----------------------------------------------------------------------------
# Members:
#   Member 1 - Sourav S       (24BKT0028) : Pretty Printer, HTML Viewer, Docs
#   Member 2 - Ram Yadav      (24BAI0201) : Lexer, Test design
#   Member 3 - Yagnesh Reddy  (24BCE0886) : Parser, AST, Semantic, Errors
#   Member 4 - Sameep         (24BCE2888) : CLI, Graphviz, JSON, Stats, Tests
# Faculty: Dr. Shalini L
# ============================================================================
# USAGE
#   python code.py <file.lang>              # text tree (default)
#   python code.py --tokens  <file.lang>    # token dump
#   python code.py --sexpr   <file.lang>    # S-expression
#   python code.py --dot     <file.lang>    # Graphviz DOT
#   python code.py --json    <file.lang>    # JSON AST (data-format compatibility)
#   python code.py --html    <file.lang>    # self-contained interactive HTML
#   python code.py --analyze <file.lang>    # semantic analysis
#   python code.py --stats   <file.lang>    # performance stats
#   python code.py --out DIR <file.lang>    # write all formats into DIR
#   python code.py --demo                   # run all built-in samples
#   python code.py --test                   # run full test suite
#   python code.py --create-samples         # write .lang files to ./samples
#   python code.py --version
# ============================================================================

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Any, Dict, Set, Tuple
import sys
import os
import time
import json
import html as html_mod
import textwrap

VERSION = "1.3.0"

# Force UTF-8 output so Unicode characters (arrows →, box-drawing ├──, etc.)
# work correctly when redirecting output to a file on Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# ============================================================================
# SECTION 1 - ERRORS  (Member 3)
# ============================================================================
class CompilerError(Exception):
    phase = "error"
    def __init__(self, message: str, line: Optional[int] = None,
                 column: Optional[int] = None):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(self.format())

    def format(self) -> str:
        loc = f" at line {self.line}, column {self.column}" if self.line else ""
        return f"[{self.phase}]{loc}: {self.message}"

    def format_with_source(self, source: str) -> str:
        """Render the error with a caret pointing at the offending column."""
        out = [self.format()]
        if self.line is not None:
            lines = source.splitlines()
            if 1 <= self.line <= len(lines):
                src = lines[self.line - 1]
                caret = " " * max(0, (self.column or 1) - 1) + "^"
                out.append("    " + src)
                out.append("    " + caret)
        return "\n".join(out)


class LexError(CompilerError):
    phase = "lexer"


class ParseError(CompilerError):
    phase = "parser"


class SemanticError(CompilerError):
    phase = "semantic"


# ============================================================================
# SECTION 2 - AST NODE MODEL  (Member 3)
# ============================================================================
class Node:
    def __init__(self, line: Optional[int] = None, column: Optional[int] = None):
        self.line = line
        self.column = column

    def head(self) -> str:
        return self.__class__.__name__

    def atoms(self) -> List[str]:
        return []

    def children(self) -> List["Node"]:
        return []

    def label(self) -> str:
        atoms = self.atoms()
        return self.head() + (f"({', '.join(atoms)})" if atoms else "")

    def to_sexpr(self) -> str:
        parts = [self.head()] + self.atoms() + [c.to_sexpr() for c in self.children()]
        return "(" + " ".join(parts) + ")"

    def count_nodes(self) -> int:
        return 1 + sum(c.count_nodes() for c in self.children())

    def depth(self) -> int:
        kids = self.children()
        return 1 if not kids else 1 + max(c.depth() for c in kids)

    def to_dict(self) -> Dict[str, Any]:
        """Machine-readable representation for JSON export."""
        d: Dict[str, Any] = {
            "kind": self.head(),
            "line": self.line,
            "column": self.column,
        }
        atoms = self.atoms()
        if atoms:
            d["attributes"] = atoms
        kids = self.children()
        if kids:
            d["children"] = [c.to_dict() for c in kids]
        return d

    def accept(self, visitor: "ASTVisitor", *args, **kwargs) -> Any:
        """Visitor pattern dispatch for clean AST traversals."""
        method_name = f"visit_{self.__class__.__name__}"
        visitor_fn = getattr(visitor, method_name, visitor.generic_visit)
        return visitor_fn(self, *args, **kwargs)


class ASTVisitor:
    """Base visitor pattern for traversing AST nodes."""
    def generic_visit(self, node: Node, *args, **kwargs) -> Any:
        results = []
        for child in node.children():
            results.append(child.accept(self, *args, **kwargs))
        return results


# ---- Program / Declarations ----
class Program(Node):
    def __init__(self, statements, line=None, column=None):
        super().__init__(line, column)
        self.statements = statements
    def head(self): return "Program"
    def children(self): return self.statements


class FunctionDecl(Node):
    def __init__(self, name, params, body, return_type=None, line=None, column=None):
        super().__init__(line, column)
        self.name, self.params, self.body, self.return_type = (
            name, params, body, return_type
        )
    def head(self): return "FunctionDecl"
    def atoms(self): return [self.name]
    def children(self): return list(self.params) + [self.body]


class Param(Node):
    def __init__(self, name, param_type=None, line=None, column=None):
        super().__init__(line, column)
        self.name, self.param_type = name, param_type
    def head(self): return "Param"
    def atoms(self): return [self.name]


class Block(Node):
    def __init__(self, statements, line=None, column=None):
        super().__init__(line, column)
        self.statements = statements
    def head(self): return "Block"
    def children(self): return self.statements


class VarDecl(Node):
    def __init__(self, var_type, name, init, line=None, column=None):
        super().__init__(line, column)
        self.var_type, self.name, self.init = var_type, name, init
    def head(self): return "VarDecl"
    def atoms(self): return [self.var_type or "let", self.name]
    def children(self): return [self.init] if self.init else []


class Assignment(Node):
    def __init__(self, name, value, line=None, column=None):
        super().__init__(line, column)
        self.name, self.value = name, value
    def head(self): return "Assign"
    def atoms(self): return [self.name]
    def children(self): return [self.value]


class IfStmt(Node):
    def __init__(self, condition, then_branch, else_branch=None,
                 line=None, column=None):
        super().__init__(line, column)
        self.condition, self.then_branch, self.else_branch = \
            condition, then_branch, else_branch
    def head(self): return "IfStmt"
    def children(self):
        kids = [self.condition, self.then_branch]
        if self.else_branch is not None:
            kids.append(self.else_branch)
        return kids


class WhileStmt(Node):
    def __init__(self, condition, body, line=None, column=None):
        super().__init__(line, column)
        self.condition, self.body = condition, body
    def head(self): return "WhileStmt"
    def children(self): return [self.condition, self.body]


class ForStmt(Node):
    def __init__(self, init, condition, update, body, line=None, column=None):
        super().__init__(line, column)
        self.init, self.condition, self.update, self.body = \
            init, condition, update, body
    def head(self): return "ForStmt"
    def children(self):
        return [c for c in [self.init, self.condition, self.update, self.body] if c is not None]


class ReturnStmt(Node):
    def __init__(self, value=None, line=None, column=None):
        super().__init__(line, column)
        self.value = value
    def head(self): return "ReturnStmt"
    def children(self): return [self.value] if self.value is not None else []


class ExprStmt(Node):
    def __init__(self, expr, line=None, column=None):
        super().__init__(line, column)
        self.expr = expr
    def head(self): return "ExprStmt"
    def children(self): return [self.expr]


class BinaryOp(Node):
    def __init__(self, op, left, right, line=None, column=None):
        super().__init__(line, column)
        self.op, self.left, self.right = op, left, right
    def head(self): return f"BinaryOp:{self.op}"
    def children(self): return [self.left, self.right]


class UnaryOp(Node):
    def __init__(self, op, operand, line=None, column=None):
        super().__init__(line, column)
        self.op, self.operand = op, operand
    def head(self): return f"UnaryOp:{self.op}"
    def children(self): return [self.operand]


class Literal(Node):
    def __init__(self, value, kind, line=None, column=None):
        super().__init__(line, column)
        self.value, self.kind = value, kind
    def head(self): return f"Literal:{self.kind}"
    def atoms(self):
        if self.kind == "string": return [f'"{self.value}"']
        if self.kind == "bool":   return ["true" if self.value else "false"]
        return [str(self.value)]


class Identifier(Node):
    def __init__(self, name, line=None, column=None):
        super().__init__(line, column)
        self.name = name
    def head(self): return "Identifier"
    def atoms(self): return [self.name]


class CallExpr(Node):
    def __init__(self, callee, args, line=None, column=None):
        super().__init__(line, column)
        self.callee, self.args = callee, args
    def head(self): return "Call"
    def atoms(self): return [self.callee]
    def children(self): return list(self.args)


# ============================================================================
# SECTION 3 - LEXER  (Member 2 - Core Module 1)
# ============================================================================
class TokenType(Enum):
    INT_LIT = auto(); FLOAT_LIT = auto(); STRING_LIT = auto(); IDENT = auto()
    KW_LET = auto(); KW_INT = auto(); KW_FLOAT = auto(); KW_BOOL = auto()
    KW_STRING = auto(); KW_VOID = auto()
    KW_IF = auto(); KW_ELSE = auto(); KW_WHILE = auto(); KW_FOR = auto()
    KW_RETURN = auto(); KW_FUNC = auto(); KW_TRUE = auto(); KW_FALSE = auto()
    PLUS = auto(); MINUS = auto(); STAR = auto(); SLASH = auto(); PERCENT = auto()
    ASSIGN = auto(); EQ = auto(); NEQ = auto(); LT = auto(); GT = auto()
    LTE = auto(); GTE = auto(); AND = auto(); OR = auto(); NOT = auto()
    LPAREN = auto(); RPAREN = auto(); LBRACE = auto(); RBRACE = auto()
    COMMA = auto(); SEMI = auto(); EOF = auto()


KEYWORDS = {
    "let": TokenType.KW_LET, "int": TokenType.KW_INT,
    "float": TokenType.KW_FLOAT, "bool": TokenType.KW_BOOL,
    "string": TokenType.KW_STRING, "void": TokenType.KW_VOID,
    "if": TokenType.KW_IF, "else": TokenType.KW_ELSE,
    "while": TokenType.KW_WHILE, "for": TokenType.KW_FOR,
    "return": TokenType.KW_RETURN, "func": TokenType.KW_FUNC,
    "true": TokenType.KW_TRUE, "false": TokenType.KW_FALSE,
}

SINGLE_CHAR = {
    "+": TokenType.PLUS, "-": TokenType.MINUS, "*": TokenType.STAR,
    "/": TokenType.SLASH, "%": TokenType.PERCENT,
    "(": TokenType.LPAREN, ")": TokenType.RPAREN,
    "{": TokenType.LBRACE, "}": TokenType.RBRACE,
    ",": TokenType.COMMA, ";": TokenType.SEMI,
}


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int
    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


class Lexer:
    def __init__(self, source: str):
        self.src = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

    def _error(self, msg):
        raise LexError(msg, self.line, self.col)

    def _peek(self, offset=0):
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else ""

    def _advance(self):
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1; self.col = 1
        else:
            self.col += 1
        return ch

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.src):
            ch = self._peek()
            if ch in " \t\r\n":
                self._advance(); continue
            if ch == "/" and self._peek(1) == "/":
                while self.pos < len(self.src) and self._peek() != "\n":
                    self._advance()
                continue
            if ch == "/" and self._peek(1) == "*":
                depth = 1
                self._advance(); self._advance()
                while self.pos < len(self.src) and depth > 0:
                    if self._peek() == "/" and self._peek(1) == "*":
                        depth += 1
                        self._advance(); self._advance()
                    elif self._peek() == "*" and self._peek(1) == "/":
                        depth -= 1
                        self._advance(); self._advance()
                    else:
                        self._advance()
                if depth > 0:
                    self._error("Unterminated block comment")
                continue
            sl, sc = self.line, self.col
            if ch.isdigit():
                self.tokens.append(self._read_number(sl, sc)); continue
            if ch == '"':
                self.tokens.append(self._read_string(sl, sc)); continue
            if ch.isalpha() or ch == "_":
                self.tokens.append(self._read_ident(sl, sc)); continue
            two = ch + self._peek(1)
            two_map = {"==": TokenType.EQ, "!=": TokenType.NEQ,
                       "<=": TokenType.LTE, ">=": TokenType.GTE,
                       "&&": TokenType.AND, "||": TokenType.OR}
            if two in two_map:
                self._advance(); self._advance()
                self.tokens.append(Token(two_map[two], two, sl, sc)); continue
            if ch == "=":
                self._advance()
                self.tokens.append(Token(TokenType.ASSIGN, "=", sl, sc)); continue
            if ch == "<":
                self._advance()
                self.tokens.append(Token(TokenType.LT, "<", sl, sc)); continue
            if ch == ">":
                self._advance()
                self.tokens.append(Token(TokenType.GT, ">", sl, sc)); continue
            if ch == "!":
                self._advance()
                self.tokens.append(Token(TokenType.NOT, "!", sl, sc)); continue
            if ch in SINGLE_CHAR:
                self._advance()
                self.tokens.append(Token(SINGLE_CHAR[ch], ch, sl, sc)); continue
            self._error(f"Unexpected character {ch!r}")
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return self.tokens

    def _read_number(self, line, col):
        start = self.pos
        while self._peek().isdigit():
            self._advance()
        is_float = False
        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            self._advance()
            while self._peek().isdigit():
                self._advance()
        text = self.src[start:self.pos]
        if is_float:
            return Token(TokenType.FLOAT_LIT, float(text), line, col)
        return Token(TokenType.INT_LIT, int(text), line, col)

    def _read_string(self, line, col):
        self._advance()
        chars = []
        while True:
            if self.pos >= len(self.src):
                raise LexError("Unterminated string literal", line, col)
            ch = self._advance()
            if ch == '"':
                break
            if ch == "\\":
                if self.pos >= len(self.src):
                    raise LexError("Unterminated string literal", line, col)
                nxt = self._advance()
                chars.append({"n": "\n", "t": "\t", "r": "\r", '"': '"',
                              "\\": "\\"}.get(nxt, nxt))
            else:
                chars.append(ch)
        return Token(TokenType.STRING_LIT, "".join(chars), line, col)

    def _read_ident(self, line, col):
        start = self.pos
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        text = self.src[start:self.pos]
        return Token(KEYWORDS.get(text, TokenType.IDENT), text, line, col)


# ============================================================================
# SECTION 4 - PARSER  (Member 3 - Core Module 2)
# ----------------------------------------------------------------------------
# Formal Grammar (EBNF Frozen Specification):
#
#   Program         ::= Statement* EOF
#   Statement       ::= FunctionDecl
#                     | VarDecl
#                     | IfStmt
#                     | WhileStmt
#                     | ForStmt
#                     | ReturnStmt
#                     | Block
#                     | ExprStmt
#
#   FunctionDecl    ::= ( "func" | Type ) IDENT "(" [ ParamList ] ")" Block
#   ParamList       ::= Param ( "," Param )*
#   Param           ::= [ Type ] IDENT
#
#   VarDecl         ::= ( "let" | Type ) IDENT [ "=" Expression ] ";"
#   Type            ::= "int" | "float" | "bool" | "string" | "void"
#
#   IfStmt          ::= "if" "(" Expression ")" Block [ "else" ( IfStmt | Block ) ]
#   WhileStmt       ::= "while" "(" Expression ")" Block
#   ForStmt         ::= "for" "(" ( VarDeclNoSemi | Assignment | Expression | empty ) ";"
#                                 [ Expression ] ";"
#                                 ( Assignment | Expression | empty ) ")" Block
#
#   ReturnStmt      ::= "return" [ Expression ] ";"
#   Block           ::= "{" Statement* "}"
#   ExprStmt        ::= ( Assignment | Expression ) ";"
#   Assignment      ::= IDENT "=" Expression
#
#   Expression      ::= LogicalOr
#   LogicalOr       ::= LogicalAnd ( "||" LogicalAnd )*
#   LogicalAnd      ::= Equality ( "&&" Equality )*
#   Equality        ::= Relational ( ( "==" | "!=" ) Relational )*
#   Relational      ::= Additive ( ( "<" | "<=" | ">" | ">=" ) Additive )*
#   Additive        ::= Multiplicative ( ( "+" | "-" ) Multiplicative )*
#   Multiplicative  ::= Unary ( ( "*" | "/" | "%" ) Unary )*
#   Unary           ::= ( "-" | "!" ) Unary | Postfix
#   Postfix         ::= Primary ( "(" [ ArgList ] ")" )*
#   ArgList         ::= Expression ( "," Expression )*
#   Primary         ::= INT_LIT | FLOAT_LIT | STRING_LIT | BOOL_LIT | IDENT | "(" Expression ")"
# ============================================================================
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors: List[ParseError] = []

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _peek_at(self, offset) -> Token:
        i = self.pos + offset
        return self.tokens[i] if i < len(self.tokens) else self.tokens[-1]

    def _check(self, ttype) -> bool:
        return self._peek().type == ttype

    def _advance(self) -> Token:
        tok = self._peek()
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def _match(self, *types):
        if self._peek().type in types:
            return self._advance()
        return None

    def _expect(self, ttype, what=None) -> Token:
        if self._peek().type == ttype:
            return self._advance()
        tok = self._peek()
        expected = what or ttype.name
        raise ParseError(
            f"Expected {expected} but found {tok.type.name} ({tok.value!r})",
            tok.line, tok.column,
        )

    def parse(self) -> Program:
        """Strict parse: raises on first error (used by tests)."""
        stmts = []
        while not self._check(TokenType.EOF):
            stmts.append(self._parse_top_level())
        return Program(stmts, line=1, column=1)

    def parse_recovering(self) -> Tuple[Program, List[ParseError]]:
        """Recovering parse: collects errors, returns partial AST."""
        stmts = []
        self.errors = []
        while not self._check(TokenType.EOF):
            if self._check(TokenType.RBRACE):
                tok = self._advance()
                self.errors.append(ParseError("Unexpected closing brace", tok.line, tok.column))
                continue
            try:
                stmts.append(self._parse_top_level())
            except ParseError as e:
                self.errors.append(e)
                self._synchronize()
        return Program(stmts, line=1, column=1), self.errors

    def _synchronize(self):
        """Error recovery: skip tokens until a statement boundary."""
        old_pos = self.pos
        self._advance()
        while not self._check(TokenType.EOF):
            if self.tokens[self.pos - 1].type == TokenType.SEMI:
                return
            if self._peek().type in (TokenType.KW_FUNC, TokenType.KW_IF,
                                     TokenType.KW_WHILE, TokenType.KW_FOR,
                                     TokenType.KW_RETURN, TokenType.KW_INT,
                                     TokenType.KW_LET, TokenType.KW_FLOAT,
                                     TokenType.KW_BOOL, TokenType.KW_STRING,
                                     TokenType.KW_VOID, TokenType.RBRACE):
                return
            self._advance()
        if self.pos <= old_pos and not self._check(TokenType.EOF):
            self._advance()

    def _parse_top_level(self):
        if self._check(TokenType.KW_FUNC):
            return self._parse_function()
        if (self._peek().type in (TokenType.KW_INT, TokenType.KW_FLOAT,
                                  TokenType.KW_BOOL, TokenType.KW_STRING,
                                  TokenType.KW_VOID)
                and self._peek_at(1).type == TokenType.IDENT
                and self._peek_at(2).type == TokenType.LPAREN):
            return self._parse_function()
        return self._parse_statement()

    def _parse_function(self):
        tok = self._advance()
        if tok.type == TokenType.KW_FUNC:
            return_type = "void"
            name_tok = self._expect(TokenType.IDENT, "function name")
        else:
            return_type = tok.value
            name_tok = self._expect(TokenType.IDENT, "function name")
        name = name_tok.value
        self._expect(TokenType.LPAREN, "'('")
        params = []
        if not self._check(TokenType.RPAREN):
            params.append(self._parse_param())
            while self._match(TokenType.COMMA):
                params.append(self._parse_param())
        self._expect(TokenType.RPAREN, "')'")
        body = self._parse_block()
        return FunctionDecl(name, params, body, return_type=return_type,
                            line=tok.line, column=tok.column)

    def _parse_param(self):
        ptype = None
        if self._peek().type in (TokenType.KW_INT, TokenType.KW_FLOAT,
                                 TokenType.KW_BOOL, TokenType.KW_STRING,
                                 TokenType.KW_LET):
            ptype = self._advance().value
        p = self._expect(TokenType.IDENT, "parameter name")
        return Param(p.value, param_type=ptype, line=p.line, column=p.column)

    def _parse_statement(self):
        tok = self._peek()
        if tok.type == TokenType.KW_FUNC:
            return self._parse_function()
        if (tok.type in (TokenType.KW_INT, TokenType.KW_FLOAT,
                         TokenType.KW_BOOL, TokenType.KW_STRING,
                         TokenType.KW_VOID)
                and self._peek_at(1).type == TokenType.IDENT
                and self._peek_at(2).type == TokenType.LPAREN):
            return self._parse_function()
        if tok.type in (TokenType.KW_INT, TokenType.KW_FLOAT,
                        TokenType.KW_BOOL, TokenType.KW_STRING,
                        TokenType.KW_VOID, TokenType.KW_LET):
            return self._parse_var_decl()
        if tok.type == TokenType.KW_IF:     return self._parse_if()
        if tok.type == TokenType.KW_WHILE:  return self._parse_while()
        if tok.type == TokenType.KW_FOR:    return self._parse_for()
        if tok.type == TokenType.KW_RETURN: return self._parse_return()
        if tok.type == TokenType.LBRACE:    return self._parse_block()
        return self._parse_expr_stmt()

    def _parse_var_decl(self, consume_semi=True):
        type_tok = self._advance()
        var_type = None if type_tok.type == TokenType.KW_LET else type_tok.value
        name_tok = self._expect(TokenType.IDENT, "variable name")
        init = None
        if self._match(TokenType.ASSIGN):
            init = self._parse_expression()
        if consume_semi:
            self._expect(TokenType.SEMI, "';' after variable declaration")
        return VarDecl(var_type, name_tok.value, init,
                       line=type_tok.line, column=type_tok.column)

    def _parse_if(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "'('")
        cond = self._parse_expression()
        self._expect(TokenType.RPAREN, "')'")
        then_branch = self._parse_block()
        else_branch = None
        if self._match(TokenType.KW_ELSE):
            if self._check(TokenType.KW_IF):
                else_branch = self._parse_if()
            else:
                else_branch = self._parse_block()
        return IfStmt(cond, then_branch, else_branch,
                      line=tok.line, column=tok.column)

    def _parse_while(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "'('")
        cond = self._parse_expression()
        self._expect(TokenType.RPAREN, "')'")
        body = self._parse_block()
        return WhileStmt(cond, body, line=tok.line, column=tok.column)

    def _parse_for(self):
        tok = self._advance()
        self._expect(TokenType.LPAREN, "'('")
        if self._peek().type in (TokenType.KW_INT, TokenType.KW_FLOAT,
                                 TokenType.KW_BOOL, TokenType.KW_STRING,
                                 TokenType.KW_VOID, TokenType.KW_LET):
            init = self._parse_var_decl(consume_semi=False)
        elif (self._peek().type == TokenType.IDENT
              and self._peek_at(1).type == TokenType.ASSIGN):
            name_tok = self._advance()
            self._advance()
            val = self._parse_expression()
            init = Assignment(name_tok.value, val,
                              line=name_tok.line, column=name_tok.column)
        elif self._check(TokenType.SEMI):
            init = None
        else:
            init = self._parse_expression()
        self._expect(TokenType.SEMI, "';' after for-init")
        cond = None
        if not self._check(TokenType.SEMI):
            cond = self._parse_expression()
        self._expect(TokenType.SEMI, "';' after for-condition")
        update = None
        if not self._check(TokenType.RPAREN):
            if (self._peek().type == TokenType.IDENT
                    and self._peek_at(1).type == TokenType.ASSIGN):
                name_tok = self._advance()
                self._advance()
                val = self._parse_expression()
                update = Assignment(name_tok.value, val,
                                    line=name_tok.line, column=name_tok.column)
            else:
                update = self._parse_expression()
        self._expect(TokenType.RPAREN, "')'")
        body = self._parse_block()
        return ForStmt(init, cond, update, body,
                       line=tok.line, column=tok.column)

    def _parse_return(self):
        tok = self._advance()
        value = None
        if not self._check(TokenType.SEMI):
            value = self._parse_expression()
        self._expect(TokenType.SEMI, "';' after return")
        return ReturnStmt(value, line=tok.line, column=tok.column)

    def _parse_block(self):
        tok = self._expect(TokenType.LBRACE, "'{'")
        stmts = []
        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            stmts.append(self._parse_statement())
        self._expect(TokenType.RBRACE, "'}'")
        return Block(stmts, line=tok.line, column=tok.column)

    def _parse_expr_stmt(self):
        node = self._parse_simple_stmt_expr()
        self._expect(TokenType.SEMI, "';'")
        if isinstance(node, Assignment):
            return node
        return ExprStmt(node, line=node.line, column=node.column)

    def _parse_simple_stmt_expr(self):
        if (self._peek().type == TokenType.IDENT
                and self._peek_at(1).type == TokenType.ASSIGN):
            name_tok = self._advance()
            self._advance()
            value = self._parse_expression()
            return Assignment(name_tok.value, value,
                              line=name_tok.line, column=name_tok.column)
        return self._parse_expression()

    def _parse_expression(self): return self._parse_or()

    def _parse_or(self):
        node = self._parse_and()
        while self._match(TokenType.OR):
            op = self.tokens[self.pos - 1]
            node = BinaryOp("||", node, self._parse_and(),
                            line=op.line, column=op.column)
        return node

    def _parse_and(self):
        node = self._parse_equality()
        while self._match(TokenType.AND):
            op = self.tokens[self.pos - 1]
            node = BinaryOp("&&", node, self._parse_equality(),
                            line=op.line, column=op.column)
        return node

    def _parse_equality(self):
        node = self._parse_comparison()
        while self._peek().type in (TokenType.EQ, TokenType.NEQ):
            op = self._advance()
            node = BinaryOp(op.value, node, self._parse_comparison(),
                            line=op.line, column=op.column)
        return node

    def _parse_comparison(self):
        node = self._parse_term()
        while self._peek().type in (TokenType.LT, TokenType.GT,
                                    TokenType.LTE, TokenType.GTE):
            op = self._advance()
            node = BinaryOp(op.value, node, self._parse_term(),
                            line=op.line, column=op.column)
        return node

    def _parse_term(self):
        node = self._parse_factor()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = self._advance()
            node = BinaryOp(op.value, node, self._parse_factor(),
                            line=op.line, column=op.column)
        return node

    def _parse_factor(self):
        node = self._parse_unary()
        while self._peek().type in (TokenType.STAR, TokenType.SLASH,
                                    TokenType.PERCENT):
            op = self._advance()
            node = BinaryOp(op.value, node, self._parse_unary(),
                            line=op.line, column=op.column)
        return node

    def _parse_unary(self):
        if self._peek().type in (TokenType.MINUS, TokenType.NOT):
            op = self._advance()
            operand = self._parse_unary()
            return UnaryOp(op.value, operand,
                           line=op.line, column=op.column)
        return self._parse_call()

    def _parse_call(self):
        node = self._parse_primary()
        while self._check(TokenType.LPAREN) and isinstance(node, Identifier):
            lp = self._advance()
            args = []
            if not self._check(TokenType.RPAREN):
                args.append(self._parse_expression())
                while self._match(TokenType.COMMA):
                    args.append(self._parse_expression())
            self._expect(TokenType.RPAREN, "')'")
            node = CallExpr(node.name, args, line=lp.line, column=lp.column)
        return node

    def _parse_primary(self):
        tok = self._peek()
        if tok.type == TokenType.INT_LIT:
            self._advance()
            return Literal(tok.value, "int", line=tok.line, column=tok.column)
        if tok.type == TokenType.FLOAT_LIT:
            self._advance()
            return Literal(tok.value, "float", line=tok.line, column=tok.column)
        if tok.type == TokenType.STRING_LIT:
            self._advance()
            return Literal(tok.value, "string", line=tok.line, column=tok.column)
        if tok.type == TokenType.KW_TRUE:
            self._advance()
            return Literal(True, "bool", line=tok.line, column=tok.column)
        if tok.type == TokenType.KW_FALSE:
            self._advance()
            return Literal(False, "bool", line=tok.line, column=tok.column)
        if tok.type == TokenType.IDENT:
            self._advance()
            return Identifier(tok.value, line=tok.line, column=tok.column)
        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN, "')'")
            return expr
        raise ParseError(
            f"Unexpected token {tok.type.name} ({tok.value!r}) in expression",
            tok.line, tok.column,
        )


# ============================================================================
# SECTION 5 - SEMANTIC ANALYZER  (Member 3 - NEW: Technical Depth)
# ----------------------------------------------------------------------------
# Performs static analysis of the AST:
#   - Builds a symbol table with nested scope tracking
#   - Detects: undeclared identifiers, redeclarations in same scope,
#              wrong function-call arity, return-outside-function
#   - Reports issues with line/column (severity: error | warning)
# ============================================================================

class SemanticIssue:
    """Structured semantic diagnostic with type, severity, location, and message."""
    def __init__(self, issue_type: str, severity: str, line: Optional[int],
                 column: Optional[int], message: str):
        self.type = issue_type     # e.g. "undeclared_identifier"
        self.severity = severity   # "error" | "warning"
        self.line = line
        self.column = column
        self.message = message

    def __str__(self):
        loc = f"{self.line}:{self.column}" if self.line else "?"
        return f"[{self.severity}] {loc}: {self.message}"

    def __repr__(self):
        return (f"SemanticIssue(type={self.type!r}, severity={self.severity!r}, "
                f"line={self.line}, col={self.column}, msg={self.message!r})")


class Scope:
    def __init__(self, parent: Optional["Scope"] = None):
        self.parent = parent
        self.symbols: Dict[str, str] = {}   # name -> kind

    def declare(self, name: str, kind: str) -> bool:
        if name in self.symbols:
            return False
        self.symbols[name] = kind
        return True

    def resolve(self, name: str) -> bool:
        s = self
        while s is not None:
            if name in s.symbols:
                return True
            s = s.parent
        return False


BUILTIN_FUNCTIONS: Dict[str, int] = {
    "print": -1,   # -1 indicates variadic arity
    "println": -1,
}


class SemanticAnalyzer:
    def __init__(self):
        self.issues: List[SemanticIssue] = []
        self.functions: Dict[str, int] = dict(BUILTIN_FUNCTIONS)      # name -> arity
        self.scope: Optional[Scope] = None
        self.in_function: int = 0
        self.node_count_checked: int = 0

    def _error(self, node, msg, issue_type="error"):
        self.issues.append(SemanticIssue(issue_type, "error",
                                         node.line, node.column, msg))

    def _warn(self, node, msg, issue_type="warning"):
        self.issues.append(SemanticIssue(issue_type, "warning",
                                         node.line, node.column, msg))

    def analyze(self, program: Program) -> List[SemanticIssue]:
        self.issues = []
        self.functions = dict(BUILTIN_FUNCTIONS)
        # Pass 1: collect function signatures (for forward references)
        for stmt in program.statements:
            if isinstance(stmt, FunctionDecl):
                if stmt.name in self.functions and stmt.name not in BUILTIN_FUNCTIONS:
                    self._error(stmt, f"Function '{stmt.name}' redeclared",
                                "redeclaration")
                self.functions[stmt.name] = len(stmt.params)
        # Pass 2: walk body
        self.scope = Scope()
        for stmt in program.statements:
            self._visit(stmt)
        return self.issues

    def _visit(self, node):
        self.node_count_checked += 1
        method = getattr(self, f"_visit_{node.__class__.__name__}", None)
        if method:
            method(node)
        else:
            # default: recurse children
            for c in node.children():
                self._visit(c)

    def _visit_Program(self, node):
        for s in node.statements:
            self._visit(s)

    def _visit_FunctionDecl(self, node):
        # Declare function name in outer scope
        if not self.scope.declare(node.name, "function"):
            # Already declared in pass 1, ignore here
            pass
        # New scope for the function body
        old = self.scope
        self.scope = Scope(parent=old)
        for p in node.params:
            if not self.scope.declare(p.name, "param"):
                self._error(p, f"Parameter '{p.name}' redeclared",
                            "redeclaration")
        self.in_function += 1
        self._visit(node.body)
        self.in_function -= 1
        self.scope = old

    def _visit_Block(self, node):
        old = self.scope
        self.scope = Scope(parent=old)
        for s in node.statements:
            self._visit(s)
        self.scope = old

    def _visit_VarDecl(self, node):
        if node.init is not None:
            self._visit(node.init)
        if not self.scope.declare(node.name, "var"):
            self._error(node, f"Variable '{node.name}' redeclared in this scope",
                        "redeclaration")

    def _visit_Assignment(self, node):
        self._visit(node.value)
        if not self.scope.resolve(node.name):
            self._error(node, f"Assignment to undeclared variable '{node.name}'",
                        "assignment_undeclared")

    def _visit_Identifier(self, node):
        if not self.scope.resolve(node.name):
            self._error(node, f"Undeclared identifier '{node.name}'",
                        "undeclared_identifier")

    def _visit_CallExpr(self, node):
        if node.callee not in self.functions:
            self._error(node, f"Call to undefined function '{node.callee}'",
                        "undefined_function")
        else:
            expected = self.functions[node.callee]
            if expected != -1 and len(node.args) != expected:
                self._error(node,
                    f"Function '{node.callee}' expects {expected} args, "
                    f"got {len(node.args)}",
                    "wrong_arity")
        for a in node.args:
            self._visit(a)

    def _visit_ReturnStmt(self, node):
        if self.in_function == 0:
            self._error(node, "'return' outside of function",
                        "return_outside_function")
        if node.value is not None:
            self._visit(node.value)

    def _visit_IfStmt(self, node):
        self._visit(node.condition)
        self._visit(node.then_branch)
        if node.else_branch is not None:
            self._visit(node.else_branch)

    def _visit_WhileStmt(self, node):
        self._visit(node.condition)
        self._visit(node.body)

    def _visit_ForStmt(self, node):
        old = self.scope
        self.scope = Scope(parent=old)
        if node.init is not None: self._visit(node.init)
        if node.condition is not None: self._visit(node.condition)
        if node.update is not None: self._visit(node.update)
        if node.body is not None: self._visit(node.body)
        self.scope = old

    def _visit_BinaryOp(self, node):
        self._visit(node.left); self._visit(node.right)

    def _visit_UnaryOp(self, node):
        self._visit(node.operand)

    def _visit_ExprStmt(self, node):
        self._visit(node.expr)

    def _visit_Literal(self, node):
        """Leaf node — no semantic checks needed."""
        pass


# ============================================================================
# SECTION 6 - PRETTY PRINTER  (Member 1)
# ============================================================================
class TextTreePrinter:
    def __init__(self, use_ascii=False):
        self.ascii = use_ascii

    def _pipes(self):
        if self.ascii:
            return "|-- ", "`-- ", "|   ", "    "
        return "├── ", "└── ", "│   ", "    "

    def render(self, node: Node) -> str:
        lines = [node.label()]
        self._walk(node, "", lines)
        return "\n".join(lines)

    def _walk(self, node, prefix, lines):
        branch, last, mid, gap = self._pipes()
        kids = node.children()
        for i, child in enumerate(kids):
            is_last = (i == len(kids) - 1)
            lines.append(prefix + (last if is_last else branch) + child.label())
            self._walk(child, prefix + (gap if is_last else mid), lines)


class SExprPrinter:
    def render(self, node: Node) -> str:
        return node.to_sexpr()


# ============================================================================
# SECTION 7 - JSON PRINTER  (Member 4 - NEW: data-format compatibility)
# ============================================================================
class JSONPrinter:
    def render(self, node: Node, indent: int = 2) -> str:
        return json.dumps(node.to_dict(), indent=indent, ensure_ascii=False)


# ============================================================================
# SECTION 8 - GRAPHVIZ VISUALIZER  (Member 4)
# ============================================================================
class GraphvizVisualizer:
    def __init__(self):
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"n{self._counter}"

    def to_dot(self, root: Node, title="AST") -> str:
        self._counter = 0
        lines = [f'digraph "{title}" {{',
                 '  rankdir=TB;',
                 '  node [shape=box, fontname="Helvetica", '
                 'style="rounded,filled", fillcolor="#e8f0fe"];']
        self._emit(root, lines, None)
        lines.append("}")
        return "\n".join(lines)

    def _emit(self, node, lines, parent_id):
        nid = self._next_id()
        label = node.label().replace('"', '\\"')
        lines.append(f'  {nid} [label="{label}"];')
        if parent_id is not None:
            lines.append(f"  {parent_id} -> {nid};")
        for c in node.children():
            self._emit(c, lines, nid)
        return nid

# ============================================================================
# SECTION 9 - HTML INTERACTIVE VISUALIZER  (Member 1 - UPGRADED)
# ============================================================================
class HTMLVisualizer:
    """Self-contained, production-grade interactive HTML AST Explorer."""

    def render(self, ast: Node, title: str = "AST Visualizer & Explorer", source: str = "") -> str:
        nodes_data = []
        node_id_counter = [0]

        def categorize(head: str) -> str:
            if head in ('Program', 'Block'): return 'structure'
            if head in ('FunctionDecl', 'Param'): return 'function'
            if head in ('VarDecl', 'Assignment'): return 'variable'
            if head in ('IfStmt', 'WhileStmt', 'ForStmt', 'ReturnStmt', 'ExprStmt'): return 'control'
            if head.startswith(('BinaryOp', 'UnaryOp')) or head == 'CallExpr': return 'expression'
            if head.startswith('Literal') or head == 'Identifier': return 'literal'
            return 'other'

        def get_category_label(cat: str) -> str:
            return {
                'structure': 'Structure',
                'function': 'Function',
                'variable': 'Variable',
                'control': 'Control Flow',
                'expression': 'Expression',
                'literal': 'Literal / Leaf',
                'other': 'Node'
            }.get(cat, 'Node')

        def build_node_hierarchy(node: Node, parent_id=None, depth=0):
            nid = f"ast_node_{node_id_counter[0]}"
            node_id_counter[0] += 1
            
            head = node.head()
            cat = categorize(head)
            label = node.label()
            kids = node.children()
            
            node_info = {
                'id': nid,
                'head': head,
                'category': cat,
                'label': label,
                'line': node.line,
                'column': node.column,
                'depth': depth,
                'total_subnodes': node.count_nodes(),
                'children_ids': [],
                'parent_id': parent_id
            }
            nodes_data.append(node_info)
            
            rendered_children = []
            for k in kids:
                child_html, cid = build_node_hierarchy(k, nid, depth + 1)
                node_info['children_ids'].append(cid)
                rendered_children.append(child_html)
                
            has_kids = len(kids) > 0
            kids_html = f'<ul class="tree-children" id="{nid}_children">{"".join(rendered_children)}</ul>' if has_kids else ""
            
            loc_badge = f'<span class="badge badge-loc" title="Source coordinate">@{node.line}:{node.column}</span>' if node.line is not None else ""
            count_badge = f'<span class="badge badge-count" title="Subtree nodes">{len(kids)} {("child" if len(kids)==1 else "children")}</span>' if has_kids else ""
            
            toggle_btn = f'<button class="tree-toggle" onclick="toggleNode(\'{nid}\', event)" title="Collapse/Expand"><svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/></svg></button>' if has_kids else '<span class="tree-toggle-placeholder"></span>'

            node_card = (
                f'<li class="tree-item" id="{nid}" data-category="{cat}" data-head="{html_mod.escape(head)}" data-line="{node.line or ''}" data-col="{node.column or ''}">'
                f'  <div class="node-row" onclick="selectNode(\'{nid}\')">'
                f'    {toggle_btn}'
                f'    <div class="node-card cat-{cat}">'
                f'      <span class="badge badge-cat badge-{cat}">{get_category_label(cat)}</span>'
                f'      <span class="node-label">{html_mod.escape(label)}</span>'
                f'      {loc_badge}'
                f'      {count_badge}'
                f'    </div>'
                f'  </div>'
                f'  {kids_html}'
                f'</li>'
            )
            return node_card, nid

        tree_html, root_id = build_node_hierarchy(ast)
        total_nodes = ast.count_nodes()
        max_depth = ast.depth()
        
        src_lines = source.splitlines() if source else []
        src_rows = []
        for idx, l in enumerate(src_lines, 1):
            escaped_l = html_mod.escape(l) if l.strip() else "&nbsp;"
            src_rows.append(f'<div class="src-line" id="src_line_{idx}"><span class="src-ln">{idx}</span><span class="src-code">{escaped_l}</span></div>')
        source_block_html = "".join(src_rows) if src_rows else '<div style="padding:16px;color:#94a3b8;font-size:12px;">No source code attached</div>'

        json_ast = JSONPrinter().render(ast)
        nodes_lookup_json = json.dumps({n['id']: n for n in nodes_data})

        return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html_mod.escape(title)}</title>
  <style>
    :root {{
      --bg-base: #0a0f1d;
      --bg-surface: #111827;
      --bg-card: #1f2937;
      --bg-hover: #374151;
      --border-color: #374151;
      --border-subtle: #1f2937;
      --text-main: #f9fafb;
      --text-muted: #9ca3af;
      --text-faint: #6b7280;
      --accent-primary: #38bdf8;
      --accent-hover: #0284c7;
      
      --cat-structure: #6366f1;
      --cat-structure-bg: rgba(99, 102, 241, 0.15);
      --cat-function: #10b981;
      --cat-function-bg: rgba(16, 185, 129, 0.15);
      --cat-variable: #0ea5e9;
      --cat-variable-bg: rgba(14, 165, 233, 0.15);
      --cat-control: #f59e0b;
      --cat-control-bg: rgba(245, 158, 11, 0.15);
      --cat-expression: #a855f7;
      --cat-expression-bg: rgba(168, 85, 247, 0.15);
      --cat-literal: #ec4899;
      --cat-literal-bg: rgba(236, 72, 153, 0.15);
      --cat-other: #64748b;
      --cat-other-bg: rgba(100, 116, 139, 0.15);
      
      --tree-line-color: #374151;
      --highlight-bg: rgba(245, 158, 11, 0.25);
      --highlight-border: #f59e0b;
    }}

    [data-theme="light"] {{
      --bg-base: #f8fafc;
      --bg-surface: #ffffff;
      --bg-card: #f1f5f9;
      --bg-hover: #e2e8f0;
      --border-color: #cbd5e1;
      --border-subtle: #e2e8f0;
      --text-main: #0f172a;
      --text-muted: #475569;
      --text-faint: #94a3b8;
      --accent-primary: #0284c7;
      --accent-hover: #0369a1;
      --tree-line-color: #cbd5e1;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg-base);
      color: var(--text-main);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    .app-header {{
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-color);
      padding: 10px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
      gap: 16px;
    }}

    .header-branding {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .logo-icon {{
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #38bdf8, #6366f1);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-weight: 900;
      font-size: 18px;
      box-shadow: 0 2px 8px rgba(56, 189, 248, 0.3);
    }}

    .header-title {{
      font-size: 17px;
      font-weight: 700;
      letter-spacing: -0.3px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .version-tag {{
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent-primary);
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 12px;
      border: 1px solid rgba(56, 189, 248, 0.3);
      font-weight: 600;
    }}

    .stats-ribbon {{
      display: flex;
      gap: 10px;
      align-items: center;
    }}

    .stat-pill {{
      display: flex;
      align-items: center;
      gap: 6px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
    }}

    .stat-val {{
      color: var(--accent-primary);
      font-weight: 700;
      font-family: Consolas, monospace;
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .btn {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
      user-select: none;
    }}

    .btn:hover {{
      background: var(--bg-hover);
      border-color: var(--accent-primary);
      color: var(--accent-primary);
    }}

    .btn-primary {{
      background: var(--accent-primary);
      border-color: var(--accent-primary);
      color: #0b1329;
    }}

    .btn-primary:hover {{
      background: var(--accent-hover);
      border-color: var(--accent-hover);
      color: #fff;
    }}

    .controls-bar {{
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-color);
      padding: 8px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-shrink: 0;
    }}

    .search-box {{
      position: relative;
      width: 280px;
    }}

    .search-input {{
      width: 100%;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 6px 10px 6px 30px;
      border-radius: 6px;
      font-size: 12.5px;
      outline: none;
      transition: border 0.2s;
    }}

    .search-input:focus {{
      border-color: var(--accent-primary);
      box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
    }}

    .search-icon {{
      position: absolute;
      left: 9px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      pointer-events: none;
    }}

    .search-count {{
      position: absolute;
      right: 8px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 11px;
      color: var(--accent-primary);
      font-weight: bold;
    }}

    .category-filters {{
      display: flex;
      gap: 6px;
      align-items: center;
    }}

    .filter-chip {{
      padding: 4px 10px;
      border-radius: 14px;
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid var(--border-color);
      background: var(--bg-card);
      color: var(--text-muted);
      transition: all 0.15s;
    }}

    .filter-chip.active, .filter-chip:hover {{
      color: var(--text-main);
      border-color: var(--accent-primary);
      background: rgba(56, 189, 248, 0.15);
    }}

    .studio-layout {{
      display: flex;
      flex: 1;
      height: calc(100vh - 105px);
      overflow: hidden;
    }}

    .panel-source {{
      width: 320px;
      background: var(--bg-surface);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      transition: width 0.2s ease;
    }}

    .panel-header {{
      padding: 10px 14px;
      background: var(--bg-card);
      border-bottom: 1px solid var(--border-color);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .source-content {{
      flex: 1;
      overflow-y: auto;
      font-family: Consolas, "Courier New", monospace;
      font-size: 12.5px;
      line-height: 1.6;
      padding: 8px 0;
    }}

    .src-line {{
      display: flex;
      padding: 1px 12px;
      transition: background 0.15s;
      cursor: pointer;
    }}

    .src-line:hover {{
      background: rgba(255, 255, 255, 0.04);
    }}

    .src-line.active-line {{
      background: rgba(56, 189, 248, 0.25);
      border-left: 3px solid var(--accent-primary);
    }}

    .src-ln {{
      width: 32px;
      color: var(--text-faint);
      user-select: none;
      text-align: right;
      padding-right: 12px;
      flex-shrink: 0;
    }}

    .src-code {{
      color: var(--text-main);
      white-space: pre;
    }}

    .panel-tree {{
      flex: 1;
      overflow: auto;
      padding: 24px 32px;
      background: var(--bg-base);
      position: relative;
    }}

    .tree-root {{
      list-style: none;
      padding-left: 0;
    }}

    .tree-children {{
      list-style: none;
      padding-left: 26px;
      position: relative;
      margin-left: 12px;
      border-left: 2px solid var(--tree-line-color);
    }}

    .tree-item {{
      margin: 6px 0;
      position: relative;
    }}

    .tree-children > .tree-item::before {{
      content: "";
      position: absolute;
      top: 16px;
      left: -26px;
      width: 24px;
      height: 2px;
      background: var(--tree-line-color);
    }}

    .node-row {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      user-select: none;
    }}

    .tree-toggle {{
      width: 20px;
      height: 20px;
      border-radius: 4px;
      border: 1px solid var(--border-color);
      background: var(--bg-card);
      color: var(--text-muted);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.2s ease, background 0.15s;
      flex-shrink: 0;
    }}

    .tree-toggle:hover {{
      background: var(--bg-hover);
      color: var(--text-main);
      border-color: var(--accent-primary);
    }}

    .tree-item.collapsed > .tree-children {{
      display: none;
    }}

    .tree-item.collapsed > .node-row .tree-toggle svg {{
      transform: rotate(-90deg);
    }}

    .tree-toggle-placeholder {{
      width: 20px;
      height: 20px;
      display: inline-block;
      flex-shrink: 0;
    }}

    .node-card {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 5px 12px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.15);
      transition: all 0.15s ease;
    }}

    .node-card:hover {{
      border-color: var(--accent-primary);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }}

    .tree-item.selected > .node-row .node-card {{
      border-color: var(--accent-primary);
      box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.4);
      background: var(--bg-card);
    }}

    .tree-item.search-match > .node-row .node-card {{
      border-color: var(--highlight-border);
      background: var(--highlight-bg);
      animation: pulse 1.5s infinite;
    }}

    @keyframes pulse {{
      0% {{ box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }}
      70% {{ box-shadow: 0 0 0 6px rgba(245, 158, 11, 0); }}
      100% {{ box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }}
    }}

    .node-label {{
      font-family: Consolas, monospace;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-main);
    }}

    .badge {{
      font-size: 10.5px;
      padding: 2px 7px;
      border-radius: 4px;
      font-weight: 600;
      letter-spacing: 0.2px;
    }}

    .badge-cat {{
      text-transform: uppercase;
      font-size: 10px;
      font-weight: 700;
    }}

    .badge-structure {{ background: var(--cat-structure-bg); color: var(--cat-structure); border: 1px solid var(--cat-structure); }}
    .badge-function {{ background: var(--cat-function-bg); color: var(--cat-function); border: 1px solid var(--cat-function); }}
    .badge-variable {{ background: var(--cat-variable-bg); color: var(--cat-variable); border: 1px solid var(--cat-variable); }}
    .badge-control {{ background: var(--cat-control-bg); color: var(--cat-control); border: 1px solid var(--cat-control); }}
    .badge-expression {{ background: var(--cat-expression-bg); color: var(--cat-expression); border: 1px solid var(--cat-expression); }}
    .badge-literal {{ background: var(--cat-literal-bg); color: var(--cat-literal); border: 1px solid var(--cat-literal); }}
    .badge-other {{ background: var(--cat-other-bg); color: var(--cat-other); border: 1px solid var(--cat-other); }}

    .badge-loc {{
      background: rgba(148, 163, 184, 0.1);
      color: var(--text-muted);
      border: 1px solid var(--border-color);
      font-family: Consolas, monospace;
    }}

    .badge-count {{
      background: var(--bg-card);
      color: var(--text-muted);
      font-size: 10px;
    }}

    .panel-inspector {{
      width: 340px;
      background: var(--bg-surface);
      border-left: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }}

    .inspector-body {{
      padding: 16px;
      flex: 1;
      overflow-y: auto;
    }}

    .insp-empty {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: var(--text-muted);
      text-align: center;
      gap: 12px;
      padding: 24px;
    }}

    .insp-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 14px;
    }}

    .insp-title {{
      font-size: 11px;
      text-transform: uppercase;
      font-weight: 700;
      color: var(--text-muted);
      margin-bottom: 8px;
      letter-spacing: 0.5px;
    }}

    .insp-node-name {{
      font-size: 16px;
      font-weight: 700;
      font-family: Consolas, monospace;
      color: var(--accent-primary);
      margin-bottom: 6px;
      word-break: break-all;
    }}

    .insp-field {{
      display: flex;
      justify-content: space-between;
      padding: 5px 0;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 12px;
    }}

    .insp-field:last-child {{ border-bottom: none; }}
    .insp-key {{ color: var(--text-muted); font-weight: 500; }}
    .insp-val {{ color: var(--text-main); font-weight: 600; font-family: Consolas, monospace; }}

    .toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--accent-primary);
      color: #0b1329;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.2s ease;
      pointer-events: none;
      z-index: 1000;
    }}

    .toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}
  </style>
</head>
<body>

  <header class="app-header">
    <div class="header-branding">
      <div class="logo-icon">&#9889;</div>
      <div>
        <div class="header-title">
          AST Visualizer & Explorer
          <span class="version-tag">BCSE307 Review 3</span>
        </div>
      </div>
    </div>

    <div class="stats-ribbon">
      <div class="stat-pill" title="Total nodes in Abstract Syntax Tree">
        <span>Nodes:</span>
        <span class="stat-val">{total_nodes}</span>
      </div>
      <div class="stat-pill" title="Maximum hierarchy depth">
        <span>Max Depth:</span>
        <span class="stat-val">{max_depth}</span>
      </div>
      <div class="stat-pill" title="Semantic Analysis Status">
        <span>Status:</span>
        <span class="stat-val" style="color: var(--cat-function)">&#10003; 0 Issues</span>
      </div>
    </div>

    <div class="header-actions">
      <button class="btn" onclick="toggleTheme()" title="Switch Light/Dark mode">&#9680; Theme</button>
      <button class="btn" onclick="copyAstJson()" title="Copy JSON AST to clipboard">&#128203; Copy JSON</button>
      <button class="btn btn-primary" onclick="window.print()" title="Print / Export PDF">&#128424; Export</button>
    </div>
  </header>

  <div class="controls-bar">
    <div class="search-box">
      <svg class="search-icon" viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M9.5 3A6.5 6.5 0 0 1 16 9.5c0 1.61-.59 3.09-1.56 4.23l.27.27h.79l5 5-1.5 1.5-5-5v-.79l-.27-.27A6.516 6.516 0 0 1 9.5 16 6.5 6.5 0 0 1 3 9.5 6.5 6.5 0 0 1 9.5 3m0 2C7 5 5 7 5 9.5S7 14 9.5 14 14 12 14 9.5 12 5 9.5 5Z"/></svg>
      <input type="text" id="searchInput" class="search-input" placeholder="Search node or label..." oninput="handleSearch(this.value)">
      <span id="searchCount" class="search-count"></span>
    </div>

    <div class="category-filters">
      <span class="filter-chip active" onclick="filterCategory('all', this)">All Nodes</span>
      <span class="filter-chip" onclick="filterCategory('function', this)">Functions</span>
      <span class="filter-chip" onclick="filterCategory('variable', this)">Variables</span>
      <span class="filter-chip" onclick="filterCategory('control', this)">Control Flow</span>
      <span class="filter-chip" onclick="filterCategory('expression', this)">Expressions</span>
      <span class="filter-chip" onclick="filterCategory('literal', this)">Literals</span>
    </div>

    <div style="display: flex; gap: 8px;">
      <button class="btn" onclick="expandAll()">&#8862; Expand All</button>
      <button class="btn" onclick="collapseAll()">&#8863; Collapse All</button>
    </div>
  </div>

  <div class="studio-layout">
    <div class="panel-source" id="sourcePanel">
      <div class="panel-header">
        <span>SOURCE CODE (.lang)</span>
        <button class="btn" style="padding: 2px 6px; font-size: 10px;" onclick="toggleSourcePanel()">Toggle</button>
      </div>
      <div class="source-content" id="sourceContainer">
        {source_block_html}
      </div>
    </div>

    <main class="panel-tree" id="treeContainer">
      <ul class="tree-root">
        {tree_html}
      </ul>
    </main>

    <aside class="panel-inspector" id="inspectorPanel">
      <div class="panel-header">
        <span>NODE INSPECTOR</span>
        <span id="inspActiveBadge" class="badge badge-structure" style="display:none;"></span>
      </div>
      <div class="inspector-body" id="inspectorContent">
        <div class="insp-empty">
          <svg viewBox="0 0 24 24" width="36" height="36" style="opacity: 0.4;"><path fill="currentColor" d="M12 2A10 10 0 0 0 2 12a10 10 0 0 0 10 10 10 10 0 0 0 10-10A10 10 0 0 0 12 2m1 15h-2v-6h2v6m0-8h-2V7h2v2Z"/></svg>
          <div>Click any AST node in the tree to inspect its properties, coordinates, and subtree structure.</div>
        </div>
      </div>
    </aside>
  </div>

  <div class="toast" id="toastMessage">Copied to clipboard!</div>

  <script>
    const NODES_DATA = {nodes_lookup_json};
    const FULL_JSON_AST = {json.dumps(json_ast)};
    let selectedNodeId = null;

    function toggleNode(nodeId, event) {{
      if (event) event.stopPropagation();
      const item = document.getElementById(nodeId);
      if (item) {{
        item.classList.toggle('collapsed');
      }}
    }}

    function expandAll() {{
      document.querySelectorAll('.tree-item').forEach(el => el.classList.remove('collapsed'));
    }}

    function collapseAll() {{
      document.querySelectorAll('.tree-children .tree-item').forEach(el => {{
        if (el.querySelector('.tree-children')) {{
          el.classList.add('collapsed');
        }}
      }});
    }}

    function selectNode(nodeId) {{
      document.querySelectorAll('.tree-item.selected').forEach(el => el.classList.remove('selected'));
      const item = document.getElementById(nodeId);
      if (!item) return;
      item.classList.add('selected');
      selectedNodeId = nodeId;

      const data = NODES_DATA[nodeId];
      if (!data) return;

      document.querySelectorAll('.src-line.active-line').forEach(el => el.classList.remove('active-line'));
      if (data.line) {{
        const srcLine = document.getElementById('src_line_' + data.line);
        if (srcLine) {{
          srcLine.classList.add('active-line');
          srcLine.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }}
      }}

      const insp = document.getElementById('inspectorContent');
      const badge = document.getElementById('inspActiveBadge');
      badge.style.display = 'inline-block';
      badge.className = 'badge badge-' + data.category;
      badge.textContent = data.category.toUpperCase();

      insp.innerHTML = `
        <div class="insp-card">
          <div class="insp-title">Selected Node</div>
          <div class="insp-node-name">${{escapeHtml(data.label)}}</div>
          <div class="insp-field"><span class="insp-key">Node Type:</span><span class="insp-val">${{escapeHtml(data.head)}}</span></div>
          <div class="insp-field"><span class="insp-key">Category:</span><span class="insp-val">${{data.category}}</span></div>
          <div class="insp-field"><span class="insp-key">Coordinates:</span><span class="insp-val">${{data.line ? 'Line ' + data.line + ', Col ' + data.column : 'N/A'}}</span></div>
          <div class="insp-field"><span class="insp-key">Tree Depth:</span><span class="insp-val">Level ${{data.depth}}</span></div>
          <div class="insp-field"><span class="insp-key">Subtree Nodes:</span><span class="insp-val">${{data.total_subnodes}}</span></div>
        </div>
        <div class="insp-card">
          <div class="insp-title">Subtree Info</div>
          <div class="insp-field"><span class="insp-key">Direct Children:</span><span class="insp-val">${{data.children_ids.length}}</span></div>
          <div class="insp-field"><span class="insp-key">Node ID:</span><span class="insp-val">${{data.id}}</span></div>
        </div>
      `;
    }}

    function handleSearch(query) {{
      query = query.trim().toLowerCase();
      const countEl = document.getElementById('searchCount');
      document.querySelectorAll('.tree-item').forEach(el => el.classList.remove('search-match'));

      if (!query) {{
        countEl.textContent = '';
        return;
      }}

      let matches = 0;
      document.querySelectorAll('.tree-item').forEach(el => {{
        const label = (el.querySelector('.node-label')?.textContent || '').toLowerCase();
        const head = (el.getAttribute('data-head') || '').toLowerCase();
        if (label.includes(query) || head.includes(query)) {{
          el.classList.add('search-match');
          matches++;
          let parent = el.parentElement.closest('.tree-item');
          while (parent) {{
            parent.classList.remove('collapsed');
            parent = parent.parentElement.closest('.tree-item');
          }}
        }}
      }});
      countEl.textContent = matches > 0 ? `${{matches}} found` : 'No match';
    }}

    function filterCategory(cat, chip) {{
      document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      document.querySelectorAll('.tree-item').forEach(el => {{
        if (cat === 'all' || el.getAttribute('data-category') === cat) {{
          el.style.opacity = '1';
          el.style.pointerEvents = 'auto';
        }} else {{
          el.style.opacity = '0.25';
        }}
      }});
    }}

    function toggleTheme() {{
      const html = document.documentElement;
      const current = html.getAttribute('data-theme') || 'dark';
      html.setAttribute('data-theme', current === 'dark' ? 'light' : 'dark');
    }}

    function toggleSourcePanel() {{
      const p = document.getElementById('sourcePanel');
      p.style.width = p.style.width === '0px' ? '320px' : '0px';
    }}

    function copyAstJson() {{
      navigator.clipboard.writeText(FULL_JSON_AST).then(() => {{
        showToast('JSON AST copied to clipboard!');
      }}).catch(() => {{
        showToast('Unable to copy automatically');
      }});
    }}

    function showToast(msg) {{
      const t = document.getElementById('toastMessage');
      t.textContent = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2000);
    }}

    function escapeHtml(str) {{
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }}

    window.addEventListener('DOMContentLoaded', () => {{
      selectNode('{root_id}');
    }});
  </script>
</body>
</html>"""



# ============================================================================
# SECTION 10 - STATISTICS  (Member 4)
# ============================================================================
class Stats:
    def __init__(self, source, tokens, ast, lex_ms, parse_ms,
                 sem_issues=None, sem_ms=0.0):
        self.source = source
        self.tokens = tokens
        self.ast = ast
        self.lex_ms = lex_ms
        self.parse_ms = parse_ms
        self.sem_issues = sem_issues or []
        self.sem_ms = sem_ms

    def report(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("AST STATISTICS".center(60))
        lines.append("=" * 60)
        lines.append(f"  Source length          : {len(self.source)} chars")
        lines.append(f"  Lines of source        : {self.source.count(chr(10)) + 1}")
        lines.append(f"  Tokens produced        : {len(self.tokens)}")
        lines.append(f"  AST nodes              : {self.ast.count_nodes()}")
        lines.append(f"  AST depth              : {self.ast.depth()}")
        lines.append(f"  Top-level declarations : {len(self.ast.statements)}")
        lines.append(f"  Lexing time            : {self.lex_ms:.3f} ms")
        lines.append(f"  Parsing time           : {self.parse_ms:.3f} ms")
        lines.append(f"  Semantic time          : {self.sem_ms:.3f} ms")
        lines.append(f"  Semantic issues        : {len(self.sem_issues)}")
        lines.append(f"  Total front-end time   : "
                     f"{self.lex_ms + self.parse_ms + self.sem_ms:.3f} ms")
        lines.append("=" * 60)
        hist: Dict[str, int] = {}
        for t in self.tokens:
            hist[t.type.name] = hist.get(t.type.name, 0) + 1
        lines.append("TOKEN HISTOGRAM")
        lines.append("-" * 60)
        for name in sorted(hist):
            lines.append(f"  {name:<20} {hist[name]:>5}")
        lines.append("=" * 60)
        return "\n".join(lines)


# ============================================================================
# SECTION 11 - CLI + PIPELINE  (Member 4)
# ============================================================================
def parse_source(source: str):
    """Full front-end pipeline: source -> tokens -> AST.
    Returns (ast, tokens, lex_ms, parse_ms)."""
    t0 = time.perf_counter()
    tokens = Lexer(source).tokenize()
    t1 = time.perf_counter()
    ast = Parser(tokens).parse()
    t2 = time.perf_counter()
    return ast, tokens, (t1 - t0) * 1000.0, (t2 - t1) * 1000.0


def parse_and_analyze(source: str):
    """Full pipeline including semantic analysis."""
    ast, tokens, lex_ms, parse_ms = parse_source(source)
    t0 = time.perf_counter()
    analyzer = SemanticAnalyzer()
    issues = analyzer.analyze(ast)
    sem_ms = (time.perf_counter() - t0) * 1000.0
    return ast, tokens, lex_ms, parse_ms, issues, sem_ms


def banner(msg: str, ch: str = "=", width: int = 70):
    print(ch * width)
    print(msg.center(width))
    print(ch * width)


def _render(source, mode):
    if mode == "analyze":
        # Phase A: collect syntax errors via recovering parser
        toks = Lexer(source).tokenize()
        _, syntax_errs = Parser(toks).parse_recovering()
        # Phase B: if parseable, run semantic analysis on a clean AST
        sem_issues: List[SemanticIssue] = []
        sem_ms = 0.0
        try:
            ast, _, lm, pm = parse_source(source)
            t0 = time.perf_counter()
            sem_issues = SemanticAnalyzer().analyze(ast)
            sem_ms = (time.perf_counter() - t0) * 1000.0
        except CompilerError:
            pass  # if strict parse fails, we still show syntax errors

        lines = []
        # Report syntax errors
        if syntax_errs:
            lines.append(f"Syntax errors: {len(syntax_errs)} error(s) found.")
            lines.append("-" * 60)
            for err in syntax_errs:
                lines.append(f"  [syntax] line {err.line}, col {err.column}: "
                             f"{err.message}")
            lines.append("")
        # Report semantic issues
        if sem_issues:
            lines.append(f"Semantic issues: {len(sem_issues)} issue(s) found.")
            lines.append("-" * 60)
            for i in sem_issues:
                lines.append(f"  [{i.type}] {i}")
        # Summary
        total = len(syntax_errs) + len(sem_issues)
        if total == 0:
            return "Semantic analysis: 0 issues. Program is semantically valid."
        lines.insert(0, f"Analysis complete: {total} issue(s) found.")
        return "\n".join(lines)

    ast, toks, lm, pm = parse_source(source)
    if mode == "tree":   return TextTreePrinter().render(ast)
    if mode == "sexpr":  return SExprPrinter().render(ast)
    if mode == "json":   return JSONPrinter().render(ast)
    if mode == "dot":    return GraphvizVisualizer().to_dot(ast, title="AST")
    if mode == "html":   return HTMLVisualizer().render(ast, title="AST")
    if mode == "tokens": return "\n".join(repr(t) for t in toks)
    if mode == "stats":
        _, _, _, _, issues, sm = parse_and_analyze(source)
        return Stats(source, toks, ast, lm, pm, issues, sm).report()
    raise ValueError(f"unknown mode {mode}")


def run_file(path: str, mode: str = "tree", out_dir: str = None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print(f"error: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(1)

    if mode not in ("html", "json", "dot"):
        banner(f"Source: {path}")
        print(source.rstrip())
        print()

    # Pre-check for lexical and syntax errors using recovering parser
    try:
        toks = Lexer(source).tokenize()
    except LexError as e:
        banner("COMPILATION FAILED (Lexical Error)", ch="!", width=70)
        print(e.format_with_source(source))
        sys.exit(2)

    if mode not in ("tokens",):
        _, parse_errs = Parser(toks).parse_recovering()
        if parse_errs:
            banner(f"COMPILATION FAILED ({len(parse_errs)} syntax error(s))", ch="!", width=70)
            for i, err in enumerate(parse_errs, 1):
                print(f"Error {i}:")
                print(err.format_with_source(source))
                print()
            sys.exit(2)

    try:
        output = _render(source, mode)
    except CompilerError as e:
        banner("COMPILATION FAILED", ch="!", width=70)
        print(e.format_with_source(source))
        sys.exit(2)

    if mode in ("html", "json", "dot"):
        print(output)
    else:
        banner(f"Output ({mode})")
        print(output)
        print()

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(path))[0]
        for m in ("tree", "sexpr", "json", "dot", "html", "tokens",
                  "stats", "analyze"):
            try:
                content = _render(source, m)
            except CompilerError:
                continue
            ext = {"tree": "tree.txt", "sexpr": "sexpr.txt",
                   "json": "json", "dot": "dot", "html": "html",
                   "tokens": "tokens.txt", "stats": "stats.txt",
                   "analyze": "analyze.txt"}[m]
            with open(os.path.join(out_dir, f"{base}.{ext}"), "w",
                      encoding="utf-8") as f:
                f.write(content)
        print(f"[saved] all formats written to {out_dir}/")


# ---- Sample programs ----
SAMPLES = {
"demo.lang": textwrap.dedent("""\
    // Team 16 - AST Visualizer demo
    func classify(x) {
        if (x < 0) {
            print("negative");
        } else {
            print("non-negative");
        }
    }

    func main() {
        let a = 5 + 3 * 2;
        int i = 0;
        while (i < 10) {
            i = i + 1;
        }
        for (let j = 0; j < 3; j = j + 1) {
            print(j);
        }
        return classify(a);
    }
"""),

"variables.lang": textwrap.dedent("""\
    // Variable Declarations
    let inferredInt = 42;
    let inferredFloat = 3.14159;
    let inferredString = "Compiler Design 2026";
    let inferredBool = true;

    int explicitInt = 100;
    float explicitFloat = 0.005;
    bool isActive = false;
    string title = "AST Visualizer / Pretty Printer";

    int uninitializedVar;
    float bufferValue;
"""),

"expressions.lang": textwrap.dedent("""\
    let x = 1 + 2 * 3 - 4 / 2 % 3;
    let y = (1 + 2) * (3 - 4);
    let z = -x + !true || (y >= 5 && x != 0);
    let s = "hello" + "world";
"""),

"if_else.lang": textwrap.dedent("""\
    // If / Else Control Flow
    int score = 85;

    if (score > 100) {
        print("Invalid score");
    } else if (score >= 90) {
        print("Grade A");
    } else if (score >= 75) {
        print("Grade B");
    } else if (score >= 60) {
        print("Grade C");
    } else {
        print("Grade F - Needs Improvement");
    }
"""),

"loops.lang": textwrap.dedent("""\
    // Loops: while and for
    int counter = 0;
    while (counter < 5) {
        print(counter);
        counter = counter + 1;
    }

    for (let i = 0; i < 10; i = i + 1) {
        print(i);
    }

    for (int step = 20; step > 0; step = step - 4) {
        print(step);
    }
"""),

"functions.lang": textwrap.dedent("""\
    func add(a, b) {
        return a + b;
    }

    func factorial(n) {
        if (n <= 1) { return 1; }
        return n * factorial(n - 1);
    }

    int result = add(3, 4);
"""),

"nested_expressions.lang": textwrap.dedent("""\
    let complexArithmetic = (((10 + 20) * (30 - 15)) / (5 + 5)) % 7;
    let deepParens = (((((1 + 2) * 3) - 4) / 5) + 6) * 7;
    let booleanPrecedence = (!false && (10 < 20 || 30 >= 40)) == (true || false && false);
    let relationalChaining = (a + b * c > d - e / f) && (g <= h || i != j);
"""),

"control_flow.lang": textwrap.dedent("""\
    int n = 10;
    if (n > 0) {
        print("positive");
    } else if (n < 0) {
        print("negative");
    } else {
        print("zero");
    }

    while (n > 0) {
        n = n - 1;
    }

    for (let i = 0; i < 5; i = i + 1) {
        print(i);
    }
"""),

"boundary_nested.lang": textwrap.dedent("""\
    let deep = (((((((((1 + 2) * 3) - 4) / 5) + 6) * 7) - 8) / 9) + 10) * 11;
"""),

"invalid_syntax.lang": textwrap.dedent("""\
    int x = ;
    if (x > 0 { print("oops"); }
    let 5 = "bad";
"""),

"semantic_errors.lang": textwrap.dedent("""\
    // Expected semantic issues:
    //   1. undeclared identifier 'y'
    //   2. wrong arity for 'add' (expects 2, got 1)
    //   3. call to undefined function 'foo'
    //   4. assignment to undeclared variable 'undeclared' (via identifier)
    //   5. redeclaration of 'x' in same scope
    //   6. return outside function
    func add(a, b) { return a + b; }
    int x = y;
    int z = add(1);
    int w = foo(1, 2);
    x = undeclared;
    int x = 99;
    return 0;
"""),

"semantic_valid.lang": textwrap.dedent("""\
    // Semantically valid program — should report 0 issues.
    func add(a, b) {
        return a + b;
    }

    func max(a, b) {
        if (a > b) {
            return a;
        } else {
            return b;
        }
    }

    int result = add(3, 4);
    int biggest = max(result, 10);

    // Nested scopes — inner 'x' does not conflict with outer 'x'
    {
        int x = 1;
        {
            int y = x + 2;
        }
    }
    {
        int x = 99;
    }
"""),

"error_recovery.lang": textwrap.dedent("""\
    // Multiple syntax errors — parser should recover and report all.
    int a = ;
    let b = 5
    if (x > 0 { print("hello"); }
    int c = 10;
    let d = ;
"""),
}


def run_demo():
    for name, src in SAMPLES.items():
        print()
        banner(f"SAMPLE: {name}", ch="#")
        print(src.rstrip())
        print()
        if name == "invalid_syntax.lang":
            # Show recovery behaviour
            try:
                toks = Lexer(src).tokenize()
                _, errs = Parser(toks).parse_recovering()
                print(">> Parser error-recovery demonstration:")
                print(f"   {len(errs)} error(s) collected without aborting.")
                for e in errs:
                    print("   " + e.format_with_source(src).replace(
                        "\n", "\n   "))
                print()
            except LexError as e:
                print(">> Lex error:")
                print(e.format_with_source(src))
                print()
            continue

        try:
            ast, toks, lm, pm, issues, sm = parse_and_analyze(src)
        except CompilerError as e:
            print(">> Compilation error:")
            print(e.format_with_source(src))
            print()
            continue

        print(">> Text tree (top 12 lines):")
        tree = TextTreePrinter().render(ast)
        print("\n".join(tree.splitlines()[:12]))
        if len(tree.splitlines()) > 12:
            print("   ... (truncated for demo)")
        print()

        if issues:
            print(f">> Semantic analysis: {len(issues)} issue(s)")
            for i in issues:
                print("   " + str(i))
            print()
        else:
            print(">> Semantic analysis: 0 issues. Program is valid.")
            print()

        print(">> Stats:")
        print(Stats(src, toks, ast, lm, pm, issues, sm).report())
        print()


def create_samples(out_dir: str = "samples"):
    os.makedirs(out_dir, exist_ok=True)
    for name, src in SAMPLES.items():
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"[created] {path}")
    print(f"\n{len(SAMPLES)} sample files written to {out_dir}/")


# ============================================================================
# SECTION 12 - TEST SUITE  (Member 4 + all)
# ============================================================================
class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.rows = []

    def check(self, name, cond, expected="", actual=""):
        status = "PASS" if cond else "FAIL"
        if cond: self.passed += 1
        else:    self.failed += 1
        self.rows.append((name, status, str(expected), str(actual)))

    def report(self):
        w_name, w_res, w_exp, w_act = 44, 6, 30, 36
        header = f"{'Test Case':<{w_name}} {'Result':<{w_res}} " \
                 f"{'Expected':<{w_exp}} {'Actual':<{w_act}}"
        print(header)
        print("-" * (w_name + w_res + w_exp + w_act + 3))
        for name, status, exp, act in self.rows:
            exp = (exp[:w_exp - 3] + "...") if len(exp) > w_exp else exp
            act = (act[:w_act - 3] + "...") if len(act) > w_act else act
            print(f"{name:<{w_name}} {status:<{w_res}} "
                  f"{exp:<{w_exp}} {act:<{w_act}}")
        print("-" * (w_name + w_res + w_exp + w_act + 3))
        total = self.passed + self.failed
        print(f"TOTAL: {self.passed}/{total} passed, {self.failed} failed")
        return self.failed == 0


def _describe_node(node):
    kids = node.children()
    return node.head() if not kids else f"{node.head()}→{kids[0].head()}"


def run_tests():
    tr = TestResult()

    # ---- LEXER ----
    toks = Lexer("let x = 42;").tokenize()
    tr.check("lexer.int_literal",
             toks[3].type == TokenType.INT_LIT and toks[3].value == 42,
             "INT_LIT(42)", f"{toks[3].type.name}({toks[3].value})")

    toks = Lexer("x == 3 && y <= 4").tokenize()
    types = [t.type for t in toks]
    tr.check("lexer.multi_char_operators",
             TokenType.EQ in types and TokenType.AND in types and TokenType.LTE in types,
             "contains EQ,AND,LTE", "all present")

    toks = Lexer('"hello\\nworld"').tokenize()
    tr.check("lexer.string_escape",
             toks[0].type == TokenType.STRING_LIT and toks[0].value == "hello\nworld",
             "escaped \\n", repr(toks[0].value))

    toks = Lexer("// comment\nlet a = 1;").tokenize()
    tr.check("lexer.line_comment_skipped",
             toks[0].type == TokenType.KW_LET, "first=KW_LET", toks[0].type.name)

    toks = Lexer("/* block */ int x;").tokenize()
    tr.check("lexer.block_comment_skipped",
             toks[0].type == TokenType.KW_INT, "first=KW_INT", toks[0].type.name)

    try:
        Lexer("let x = @;").tokenize(); ok = False; got = "no error"
    except LexError:
        ok = True; got = "LexError"
    tr.check("lexer.invalid_char_raises", ok, "LexError raised", got)

    try:
        Lexer('"unterminated').tokenize(); ok = False; got = "no error"
    except LexError:
        ok = True; got = "LexError"
    tr.check("lexer.unterminated_string", ok, "LexError raised", got)

    # ---- PARSER ----
    ast, *_ = parse_source("int x = 1 + 2 * 3;")
    tr.check("parser.var_decl_with_precedence",
             isinstance(ast.statements[0], VarDecl)
             and ast.statements[0].init.head() == "BinaryOp:+",
             "VarDecl→BinaryOp:+", _describe_node(ast.statements[0]))

    ast, *_ = parse_source("if (a > 0) { print(a); } else { print(0); }")
    if_stmt = ast.statements[0]
    tr.check("parser.if_else",
             isinstance(if_stmt, IfStmt) and if_stmt.else_branch is not None,
             "IfStmt with else",
             "IfStmt with else" if if_stmt.else_branch is not None else "no else")

    ast, *_ = parse_source("func add(a, b) { return a + b; }")
    tr.check("parser.function_decl",
             isinstance(ast.statements[0], FunctionDecl)
             and len(ast.statements[0].params) == 2,
             "FunctionDecl 2 params",
             f"FunctionDecl {len(ast.statements[0].params)} params")

    ast, *_ = parse_source("for (let i = 0; i < 3; i = i + 1) { print(i); }")
    tr.check("parser.for_loop",
             isinstance(ast.statements[0], ForStmt),
             "ForStmt", ast.statements[0].head())

    ast, *_ = parse_source("let deep = ((((1 + 2) * 3) - 4) / 5);")
    tr.check("parser.boundary_nested_parens",
             ast.statements[0].init.head() == "BinaryOp:/",
             "BinaryOp:/", ast.statements[0].init.head())

    try:
        parse_source("int x = ;"); ok = False; got = "no error"
    except ParseError:
        ok = True; got = "ParseError"
    tr.check("parser.missing_expr_raises", ok, "ParseError raised", got)

    try:
        parse_source("if (x > 0 { print(x); }"); ok = False; got = "no error"
    except ParseError:
        ok = True; got = "ParseError"
    tr.check("parser.missing_paren_raises", ok, "ParseError raised", got)

    try:
        parse_source("let x = 1"); ok = False; got = "no error"
    except ParseError:
        ok = True; got = "ParseError"
    tr.check("parser.missing_semicolon_raises", ok, "ParseError raised", got)

    ast, *_ = parse_source("")
    tr.check("parser.empty_program",
             isinstance(ast, Program) and len(ast.statements) == 0,
             "Program 0 stmts", f"Program {len(ast.statements)} stmts")

    ast, *_ = parse_source("1 + 2;")
    tr.check("parser.single_expression_stmt",
             isinstance(ast.statements[0], ExprStmt),
             "ExprStmt", ast.statements[0].head())

    # ---- ERROR RECOVERY ----
    toks = Lexer("int x = ; int y = 5; let z = 3").tokenize()
    partial, errs = Parser(toks).parse_recovering()
    tr.check("parser.error_recovery_collects_multiple",
             len(errs) >= 2 and len(partial.statements) >= 1,
             ">=2 errors, >=1 recovered stmt",
             f"{len(errs)} errors, {len(partial.statements)} stmts")

    # ---- PRINTERS ----
    ast, *_ = parse_source("int x = 1;")
    tree = TextTreePrinter().render(ast)
    tr.check("printer.text_tree_contains_nodes",
             "Program" in tree and "VarDecl" in tree and "Literal:int" in tree,
             "Program,VarDecl,Literal:int",
             "all 3 found" if all(k in tree for k in ("Program", "VarDecl", "Literal:int")) else "missing")

    sexpr = SExprPrinter().render(ast)
    balanced = sexpr.count("(") == sexpr.count(")")
    tr.check("printer.sexpr_well_formed",
             sexpr.startswith("(Program") and balanced,
             "starts (Program, balanced",
             f"({sexpr.count('(')}/{sexpr.count(')')})")

    # ---- JSON OUTPUT (NEW) ----
    js = JSONPrinter().render(ast)
    try:
        data = json.loads(js)
        valid_json = data.get("kind") == "Program"
    except Exception:
        valid_json = False
    tr.check("json.ast_serializes",
             valid_json, "valid JSON with kind=Program",
             "valid JSON, kind=Program" if valid_json else "invalid")

    # ---- HTML OUTPUT (NEW) ----
    html_out = HTMLVisualizer().render(ast, "test")
    tr.check("html.output_well_formed",
             html_out.startswith("<!DOCTYPE html>")
             and "</html>" in html_out
             and "Program" in html_out,
             "<!DOCTYPE...>, closes html, has Program",
             "well formed" if (html_out.startswith("<!DOCTYPE html>")
                               and "</html>" in html_out) else "malformed")

    # ---- VISUALIZER ----
    dot = GraphvizVisualizer().to_dot(ast, "test")
    tr.check("visualizer.dot_well_formed",
             dot.startswith("digraph") and dot.strip().endswith("}"),
             "digraph ... }",
             "digraph ... }" if dot.startswith("digraph") else "malformed")

    # ---- STATS ----
    ast, toks, lm, pm = parse_source("let x = 1 + 2 * 3;")
    tr.check("stats.node_count_positive",
             ast.count_nodes() > 0 and ast.depth() >= 2,
             "nodes>0, depth>=2",
             f"nodes={ast.count_nodes()}, depth={ast.depth()}")

    # ---- SEMANTIC ANALYSIS ----
    # Valid program: 0 issues
    ast, *_ = parse_source("""
        func add(a, b) { return a + b; }
        int result = add(3, 4);
    """)
    issues = SemanticAnalyzer().analyze(ast)
    tr.check("semantic.valid_program_zero_issues",
             len(issues) == 0,
             "0 issues", f"{len(issues)} issues")

    # Valid nested scopes (same variable name in different scopes)
    ast, *_ = parse_source("{ int x = 1; } { int x = 2; }")
    issues = SemanticAnalyzer().analyze(ast)
    tr.check("semantic.valid_nested_scopes",
             len(issues) == 0,
             "0 issues", f"{len(issues)} issues")

    # Valid function with return
    ast, *_ = parse_source("func f() { return 1; }")
    issues = SemanticAnalyzer().analyze(ast)
    tr.check("semantic.valid_return_inside_function",
             len(issues) == 0,
             "0 issues", f"{len(issues)} issues")

    # Valid: builtin call (variadic arity)
    ast, *_ = parse_source("print(1, 2, 3);")
    issues = SemanticAnalyzer().analyze(ast)
    tr.check("semantic.valid_builtin_variadic_call",
             len(issues) == 0,
             "0 issues", f"{len(issues)} issues")

    # 1) Undeclared identifier
    ast, *_ = parse_source("int x = y;")
    issues = SemanticAnalyzer().analyze(ast)
    tr.check("semantic.undeclared_identifier",
             any(i.type == "undeclared_identifier" for i in issues),
             "type=undeclared_identifier",
             ", ".join(i.type for i in issues) or "none")

    # 2) Redeclaration in same scope
    ast, *_ = parse_source("int x = 1; int x = 2;")
    issues = SemanticAnalyzer().analyze(ast)
    tr.check("semantic.redeclaration_detected",
             any(i.type == "redeclaration" for i in issues),
             "type=redeclaration",
             ", ".join(i.type for i in issues) or "none")

    # 3) Wrong arity
    ast, *_ = parse_source("""
        func f(a, b) { return a + b; }
        int x = f(1);
    """)
    issues = SemanticAnalyzer().analyze(ast)
    tr.check("semantic.wrong_arity_detected",
             any(i.type == "wrong_arity" for i in issues),
             "type=wrong_arity",
             ", ".join(i.type for i in issues) or "none")

    # 4) Return outside function
    ast, *_ = parse_source("return 5;")
    issues = SemanticAnalyzer().analyze(ast)
    tr.check("semantic.return_outside_function",
             any(i.type == "return_outside_function" for i in issues),
             "type=return_outside_function",
             ", ".join(i.type for i in issues) or "none")

    # 5) Assignment to undeclared variable
    ast, *_ = parse_source("missing = 42;")
    issues = SemanticAnalyzer().analyze(ast)
    tr.check("semantic.assignment_to_undeclared",
             any(i.type == "assignment_undeclared" for i in issues),
             "type=assignment_undeclared",
             ", ".join(i.type for i in issues) or "none")

    # 6) Call to undefined function
    ast, *_ = parse_source("int x = ghost(1, 2);")
    issues = SemanticAnalyzer().analyze(ast)
    tr.check("semantic.undefined_function_call",
             any(i.type == "undefined_function" for i in issues),
             "type=undefined_function",
             ", ".join(i.type for i in issues) or "none")

    # 7) Multiple semantic errors in one program
    ast, *_ = parse_source("""
        int x = y;
        int x = 2;
        return 0;
    """)
    issues = SemanticAnalyzer().analyze(ast)
    types_found = {i.type for i in issues}
    tr.check("semantic.multiple_errors_collected",
             len(issues) >= 3 and "undeclared_identifier" in types_found
             and "redeclaration" in types_found
             and "return_outside_function" in types_found,
             ">=3 issues, 3 types",
             f"{len(issues)} issues: {types_found}")

    # 8) SemanticIssue has correct fields
    ast, *_ = parse_source("int x = y;")
    issues = SemanticAnalyzer().analyze(ast)
    issue = issues[0] if issues else None
    tr.check("semantic.issue_has_all_fields",
             issue is not None and hasattr(issue, 'type')
             and hasattr(issue, 'severity') and hasattr(issue, 'line')
             and hasattr(issue, 'column') and hasattr(issue, 'message'),
             "type,severity,line,column,message",
             "all present" if issue else "no issue")

    # ---- ERROR RECOVERY (extended) ----
    # Multiple syntax errors should be collected
    toks = Lexer("int a = ; let b = 5 if (x > 0 { } int c = ;").tokenize()
    partial, errs = Parser(toks).parse_recovering()
    tr.check("parser.error_recovery_multi_errors",
             len(errs) >= 3,
             ">=3 errors",
             f"{len(errs)} errors")

    # Error recovery should still produce partial valid statements
    toks = Lexer("int valid = 1; int bad = ; int also_valid = 2;").tokenize()
    partial, errs = Parser(toks).parse_recovering()
    tr.check("parser.error_recovery_partial_ast",
             len(partial.statements) >= 2 and len(errs) >= 1,
             ">=2 stmts, >=1 error",
             f"{len(partial.statements)} stmts, {len(errs)} errors")

    # ---- CORPUS (52 programs) ----
    programs = [
        "int x = 1;",
        "int x = 1 + 2;",
        "int x = 1 + 2 * 3;",
        "int x = (1 + 2) * 3;",
        "int x = -5;",
        "let y = !true;",
        "let z = a && b || c;",
        "let z = a == b && c != d;",
        "let z = a <= b && c >= d;",
        "let s = \"hi\";",
        "let b = true;",
        "let b = false;",
        "let f = 3.14;",
        "let f = 3.14 + 2.71;",
        "if (x) { y = 1; }",
        "if (x) { y = 1; } else { y = 2; }",
        "if (x) { y = 1; } else if (z) { y = 2; } else { y = 3; }",
        "while (x < 10) { x = x + 1; }",
        "for (let i = 0; i < 10; i = i + 1) { x = x + i; }",
        "func f() { return 1; }",
        "func f(a) { return a; }",
        "func f(a, b) { return a + b; }",
        "func f(a, b, c) { return a + b + c; }",
        "func f(a, b, c, d) { return a + b + c + d; }",
        "int x = f(1);",
        "int x = f(1, 2);",
        "int x = f(1, 2, 3);",
        "int x = f(1 + 2, 3 * 4);",
        "{ int x = 1; }",
        "{ { int x = 1; } }",
        "{ { { int x = 1; } } }",
        "let a = 1; let b = 2; let c = 3;",
        "int a = 1; if (a) { a = 2; } while (a < 5) { a = a + 1; }",
        "func fib(n) { if (n <= 1) { return n; } return fib(n - 1) + fib(n - 2); }",
        "let x = ((1));",
        "let x = ((((1))));",
        "let x = 1 + (2 + (3 + (4 + 5)));",
        "let x = a || b || c || d;",
        "let x = a && b && c && d;",
        "let x = a + b - c + d - e;",
        "let x = a * b / c * d / e;",
        "let x = a == b == c;",
        "return;",
        "func f() { return; }",
        "print(1);",
        "print(1, 2);",
        "print(1, 2, 3);",
        "let x = f(g(h(1)));",
        "int veryLongVariableName = 1234567890;",
        "let nested = ((a + b) * (c - d)) / ((e + f) * (g - h));",
        "let chain = a && b && c || d && e || f && g;",
        "func complex(a, b) { let c = a + b; if (c > 0) { return c; } else { return -c; } }",
    ]

    ok_count = 0
    for src in programs:
        try:
            parse_source(src)
            ok_count += 1
        except CompilerError:
            pass
    pct = 100.0 * ok_count / len(programs)
    tr.check(f"corpus.valid_programs_{len(programs)}_total",
             pct >= 95.0,
             ">=95% parse success",
             f"{pct:.1f}% ({ok_count}/{len(programs)})")

    return tr.report()


# ============================================================================
# MAIN
# ============================================================================
def _print_usage():
    print(f"AST Visualizer / Pretty Printer v{VERSION}")
    print("Team 16 | Project ID M13 | BCSE307")
    print()
    print("USAGE")
    print("  python code.py <file.lang>               # text tree (default)")
    print("  python code.py --tokens  <file.lang>     # token dump")
    print("  python code.py --sexpr   <file.lang>     # S-expression")
    print("  python code.py --json    <file.lang>     # JSON AST")
    print("  python code.py --dot     <file.lang>     # Graphviz DOT")
    print("  python code.py --html    <file.lang>     # interactive HTML")
    print("  python code.py --analyze <file.lang>     # semantic analysis")
    print("  python code.py --stats   <file.lang>     # performance stats")
    print("  python code.py --out DIR <file.lang>     # write all formats into DIR")
    print("  python code.py --demo                    # run all built-in samples")
    print("  python code.py --test                    # run full test suite")
    print("  python code.py --create-samples          # write .lang files to ./samples")
    print("  python code.py --version")


def main():
    args = sys.argv[1:]
    if not args:
        _print_usage(); return
    if args[0] in ("-h", "--help"):
        _print_usage(); return
    if args[0] == "--version":
        print(f"AST Visualizer / Pretty Printer v{VERSION} (BCSE307 Review 3 Final)")
        print("Team 16 | Project ID: M13 | Pure Python 3.7+ (Zero Dependencies)")
        return
    if args[0] == "--demo":
        run_demo(); return
    if args[0] == "--test":
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if args[0] == "--create-samples":
        create_samples(); return
    if args[0] == "--out":
        if len(args) < 3:
            print("error: --out needs DIR and FILE", file=sys.stderr)
            sys.exit(1)
        run_file(args[2], mode="tree", out_dir=args[1]); return

    mode_map = {"--tokens": "tokens", "--sexpr": "sexpr",
                "--json": "json", "--dot": "dot", "--html": "html",
                "--analyze": "analyze", "--stats": "stats"}
    if args[0] in mode_map:
        if len(args) < 2:
            print(f"error: {args[0]} needs a file", file=sys.stderr)
            sys.exit(1)
        run_file(args[1], mode=mode_map[args[0]]); return

    run_file(args[0], mode="tree")


if __name__ == "__main__":
    main()
