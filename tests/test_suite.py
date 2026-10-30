"""BCSE307 Compiler Design - Complete Automated Test Suite
Team 16 | Project ID: M13 | Evaluator: Dr. Shalini L

Covers:
  - Positive / Valid Language Constructs
  - Negative / Syntax & Lexical Error Diagnostics
  - Boundary Cases (Deep Nesting, Empty Program, Edge Literals)
  - Stress Testing (1,000 Statements)
  - Two-Pass Semantic Analysis (Scoping, Redeclaration, Arity)
  - Regression Testing (Comments-only, Partial AST Recovery)
  - Integration & Multi-Format Exporters (Text, S-Expr, JSON, DOT, HTML)

Can be executed with:
  python tests/test_suite.py
  python -m unittest tests/test_suite.py
"""
import sys
import unittest
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import code as compiler


class TestLexer(unittest.TestCase):
    """Lexical Analysis & Scanner Unit Tests (Member 2: Ram Yadav)."""

    def test_integer_and_float_literals(self):
        source = "let a = 42; let b = 3.1415;"
        lexer = compiler.Lexer(source)
        tokens = lexer.tokenize()
        token_types = [t.type for t in tokens]
        self.assertIn(compiler.TokenType.INT_LIT, token_types)
        self.assertIn(compiler.TokenType.FLOAT_LIT, token_types)
        int_tok = next(t for t in tokens if t.type == compiler.TokenType.INT_LIT)
        self.assertEqual(int_tok.value, 42)

    def test_multi_char_operators(self):
        source = "a == b && c <= d || e != f;"
        tokens = compiler.Lexer(source).tokenize()
        types = [t.type for t in tokens]
        self.assertIn(compiler.TokenType.EQ, types)
        self.assertIn(compiler.TokenType.AND, types)
        self.assertIn(compiler.TokenType.LTE, types)
        self.assertIn(compiler.TokenType.OR, types)
        self.assertIn(compiler.TokenType.NEQ, types)

    def test_string_escape_sequences(self):
        source = 'let str = "hello\\nworld\\t\\\"escaped\\\"";'
        tokens = compiler.Lexer(source).tokenize()
        str_tok = next(t for t in tokens if t.type == compiler.TokenType.STRING_LIT)
        self.assertEqual(str_tok.value, 'hello\nworld\t"escaped"')

    def test_comments_skipping(self):
        source = """
        // This is a single line comment
        let x = 10; /* block comment
        multiline */
        let y = 20;
        """
        tokens = compiler.Lexer(source).tokenize()
        identifiers = [t.value for t in tokens if t.type == compiler.TokenType.IDENT]
        self.assertEqual(identifiers, ["x", "y"])

    def test_invalid_character_diagnostic(self):
        source = "let x = @ + 5;"
        with self.assertRaises(compiler.LexError) as ctx:
            compiler.Lexer(source).tokenize()
        self.assertIn("Unexpected character", str(ctx.exception))

    def test_unterminated_string_diagnostic(self):
        source = 'let x = "unterminated string;'
        with self.assertRaises(compiler.LexError) as ctx:
            compiler.Lexer(source).tokenize()
        self.assertIn("Unterminated string", str(ctx.exception))


class TestParser(unittest.TestCase):
    """Recursive-Descent Parser & AST Construction Tests (Member 3: Yagnesh Reddy)."""

    def test_variable_declaration_precedence(self):
        source = "let x = 1 + 2 * 3;"
        ast = compiler.Parser(compiler.Lexer(source).tokenize()).parse()
        self.assertIsInstance(ast, compiler.Program)
        self.assertEqual(len(ast.statements), 1)
        stmt = ast.statements[0]
        self.assertIsInstance(stmt, compiler.VarDecl)
        # 1 + (2 * 3)
        self.assertIsInstance(stmt.init, compiler.BinaryOp)
        self.assertEqual(stmt.init.op, "+")
        self.assertIsInstance(stmt.init.right, compiler.BinaryOp)
        self.assertEqual(stmt.init.right.op, "*")

    def test_control_flow_if_else_and_loops(self):
        source = """
        if (x > 0) {
            let y = 1;
        } else {
            let y = 0;
        }
        while (y < 10) {
            y = y + 1;
        }
        for (let i = 0; i < 5; i = i + 1) {
            print(i);
        }
        """
        ast = compiler.Parser(compiler.Lexer(source).tokenize()).parse()
        self.assertEqual(len(ast.statements), 3)
        self.assertIsInstance(ast.statements[0], compiler.IfStmt)
        self.assertIsInstance(ast.statements[1], compiler.WhileStmt)
        self.assertIsInstance(ast.statements[2], compiler.ForStmt)

    def test_function_declaration_and_calls(self):
        source = """
        func add(a, b) {
            return a + b;
        }
        let res = add(5, 10);
        """
        ast = compiler.Parser(compiler.Lexer(source).tokenize()).parse()
        self.assertEqual(len(ast.statements), 2)
        fn = ast.statements[0]
        self.assertIsInstance(fn, compiler.FunctionDecl)
        self.assertEqual(fn.name, "add")
        self.assertEqual(len(fn.params), 2)

    def test_syntax_error_missing_semicolon(self):
        source = "let a = 5\nlet b = 10;"
        with self.assertRaises(compiler.ParseError):
            compiler.Parser(compiler.Lexer(source).tokenize()).parse()


class TestSemanticAnalysis(unittest.TestCase):
    """Two-Pass Semantic Analysis & Scoping Tests (Member 3: Yagnesh Reddy)."""

    def test_valid_scoping_and_functions(self):
        source = """
        func square(n) {
            return n * n;
        }
        let a = 10;
        let b = square(a);
        """
        ast, _, _, _, issues, _ = compiler.parse_and_analyze(source)
        self.assertEqual(len(issues), 0)

    def test_undeclared_identifier_detection(self):
        source = "let x = y + 1;"
        _, _, _, _, issues, _ = compiler.parse_and_analyze(source)
        issue_types = [i.type for i in issues]
        self.assertIn("undeclared_identifier", issue_types)

    def test_redeclaration_in_same_scope(self):
        source = """
        let x = 10;
        let x = 20;
        """
        _, _, _, _, issues, _ = compiler.parse_and_analyze(source)
        issue_types = [i.type for i in issues]
        self.assertIn("redeclaration", issue_types)

    def test_wrong_function_arity(self):
        source = """
        func calculate(x, y) {
            return x + y;
        }
        let val = calculate(5);
        """
        _, _, _, _, issues, _ = compiler.parse_and_analyze(source)
        issue_types = [i.type for i in issues]
        self.assertIn("wrong_arity", issue_types)

    def test_return_outside_function(self):
        source = "let x = 5;\nreturn x;"
        _, _, _, _, issues, _ = compiler.parse_and_analyze(source)
        issue_types = [i.type for i in issues]
        self.assertIn("return_outside_function", issue_types)


class TestBoundaryAndStress(unittest.TestCase):
    """Boundary & Stress Scenarios (Member 4: Sameep)."""

    def test_empty_program(self):
        ast, tokens, _, _, issues, _ = compiler.parse_and_analyze("")
        self.assertEqual(len(ast.statements), 0)
        self.assertEqual(len(issues), 0)

    def test_deeply_nested_parentheses(self):
        depth = 20
        expr = "(" * depth + "42" + ")" * depth
        source = f"let x = {expr};"
        ast, _, _, _, issues, _ = compiler.parse_and_analyze(source)
        self.assertEqual(len(issues), 0)
        self.assertIsInstance(ast.statements[0], compiler.VarDecl)

    def test_panic_mode_partial_ast(self):
        source = "let a = 1; let bad = ; let b = 2;"
        parser = compiler.Parser(compiler.Lexer(source).tokenize())
        ast, errors = parser.parse_recovering()
        self.assertGreaterEqual(len(errors), 1)
        self.assertEqual(len(ast.statements), 2)  # Recovered 'a' and 'b'

    def test_stress_thousand_statements(self):
        source = "\n".join(f"let var_{i} = {i};" for i in range(1000))
        ast, tokens, _, _, issues, _ = compiler.parse_and_analyze(source)
        self.assertEqual(len(ast.statements), 1000)
        self.assertEqual(len(issues), 0)


class TestOutputFormats(unittest.TestCase):
    """Multi-Format Visualizers & Exporters (Member 1: Sourav S)."""

    def setUp(self):
        self.source = "func add(a, b) { return a + b; } let ans = add(1, 2);"
        self.ast, _, _, _, _, _ = compiler.parse_and_analyze(self.source)

    def test_unicode_text_tree(self):
        text = compiler.TextTreePrinter().render(self.ast)
        self.assertIn("Program", text)
        self.assertIn("FunctionDecl", text)
        self.assertIn("VarDecl", text)

    def test_sexpr_printer(self):
        sexpr = compiler.SExprPrinter().render(self.ast)
        self.assertTrue(sexpr.startswith("(Program"))
        self.assertEqual(sexpr.count("("), sexpr.count(")"))

    def test_json_ast_serialization(self):
        json_str = compiler.JSONPrinter().render(self.ast)
        self.assertIn('"kind": "Program"', json_str)
        self.assertIn('"kind": "FunctionDecl"', json_str)

    def test_graphviz_dot_digraph(self):
        dot = compiler.GraphvizVisualizer().to_dot(self.ast)
        self.assertTrue(dot.startswith('digraph "AST" {') or dot.startswith("digraph AST {"))
        self.assertTrue(dot.strip().endswith("}"))

    def test_interactive_html_visualizer(self):
        html = compiler.HTMLVisualizer().render(self.ast, title="Unit Test Tree")
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("AST Visualizer", html)
        self.assertIn("FunctionDecl", html)


if __name__ == "__main__":
    unittest.main()
