#!/usr/bin/env python3
"""
AST Visualizer & Compiler Studio - Flask Backend API
Course: BCSE307 - Compiler Design | Team 16 | Project ID: M13
Faculty: Dr. Shalini L | SCOPE, VIT Vellore

Serves REST API endpoints integrating the existing code.py compiler engine.
"""

from __future__ import annotations
import sys
import os

# -----------------------------------------------------------------------------
# PREVENT STDLIB 'code' SHADOWING
# Python's stdlib modules (like pdb, click, inspect) may 'import code'.
# Preload stdlib 'code' first by temporarily excluding current working directory.
# -----------------------------------------------------------------------------
_orig_path = list(sys.path)
_cwd = os.path.dirname(os.path.abspath(__file__))
sys.path = [p for p in sys.path if p and p != '.' and os.path.abspath(p) != _cwd]
try:
    import code as _stdlib_code
finally:
    sys.path = _orig_path

import io
import time
import json
import traceback
import importlib.util
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify, render_template, send_from_directory

# -----------------------------------------------------------------------------
# DYNAMIC COMPILER IMPORT
# -----------------------------------------------------------------------------
BASE_DIR = _cwd
CODE_PATH = os.path.join(BASE_DIR, "code.py")

if not os.path.exists(CODE_PATH):
    raise FileNotFoundError(f"Compiler source file not found at {CODE_PATH}")

spec = importlib.util.spec_from_file_location("compiler_core", CODE_PATH)
compiler = importlib.util.module_from_spec(spec)
sys.modules["compiler_core"] = compiler
spec.loader.exec_module(compiler)

# -----------------------------------------------------------------------------
# FLASK APPLICATION SETUP
# -----------------------------------------------------------------------------
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static"
)
app.config["JSON_AS_ASCII"] = False
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024  # 1MB limit for student source codes

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

# -----------------------------------------------------------------------------
# METADATA DICTIONARIES FOR SAMPLES
# -----------------------------------------------------------------------------
SAMPLE_METADATA = {
    "demo.lang": {
        "title": "Comprehensive Compiler Demo",
        "category": "Core Basics",
        "description": "Demonstrates functions with parameters, if-else branching, while loops, for loops, arithmetic expressions, and function returns.",
        "expectedOutcome": "Valid compilation: 52 AST nodes, 0 semantic issues, full multi-format rendering."
    },
    "variables.lang": {
        "title": "Variable Declarations & Types",
        "category": "Core Basics",
        "description": "Tests type inference ('let') and explicit types ('int', 'float', 'string', 'bool'), including uninitialized declarations.",
        "expectedOutcome": "Valid compilation: series of VarDecl nodes with correct type attributes."
    },
    "expressions.lang": {
        "title": "Operator Precedence & Associativity",
        "category": "Expressions",
        "description": "Tests 8-level precedence climbing: multiplicative (*, /, %) over additive (+, -), relational over equality, and logical operators.",
        "expectedOutcome": "Valid compilation: deeply nested BinaryOp nodes reflecting correct mathematical binding order."
    },
    "nested_expressions.lang": {
        "title": "Complex Nested Expressions",
        "category": "Expressions",
        "description": "Deeply parenthesized arithmetic, boolean logic chains, and relational comparisons.",
        "expectedOutcome": "Valid compilation: structured AST respecting explicit parenthesization."
    },
    "boundary_nested.lang": {
        "title": "Deep Boundary Stress Test",
        "category": "Boundary & Stress",
        "description": "Extreme parenthesis depth (depth 10+) verifying recursive descent parser robustness without stack overflow.",
        "expectedOutcome": "Valid compilation: maximum AST depth reached cleanly with 0 parser errors."
    },
    "if_else.lang": {
        "title": "If / Else-If / Else Ladder",
        "category": "Control Flow",
        "description": "Multi-way conditional statements verifying recursive else-branch parsing and nested block resolution.",
        "expectedOutcome": "Valid compilation: chained IfStmt nodes with correct nested then/else branches."
    },
    "loops.lang": {
        "title": "While & For Loop Constructs",
        "category": "Control Flow",
        "description": "Tests while-loop conditions and for-loop 3-part header (initializer, condition, step update) with block bodies.",
        "expectedOutcome": "Valid compilation: WhileStmt and ForStmt AST nodes with correct sub-trees."
    },
    "control_flow.lang": {
        "title": "Mixed Control Flow Patterns",
        "category": "Control Flow",
        "description": "Combines conditionals and nested iteration within sequential top-level blocks.",
        "expectedOutcome": "Valid compilation: cleanly structured control flow blocks."
    },
    "functions.lang": {
        "title": "Function Declarations & Recursion",
        "category": "Functions",
        "description": "Tests multi-parameter function signatures, recursive calls (factorial), and return statements.",
        "expectedOutcome": "Valid compilation: FunctionDecl, Param, CallExpr nodes with verified call arity."
    },
    "semantic_valid.lang": {
        "title": "Semantically Valid Scoped Program",
        "category": "Semantic Analysis",
        "description": "Demonstrates nested block scoping `{}` where identical variable names in separate blocks do not conflict.",
        "expectedOutcome": "Valid compilation: Semantic Analyzer reports exactly 0 issues."
    },
    "invalid_syntax.lang": {
        "title": "Syntax Errors & Panic Recovery",
        "category": "Diagnostics & Errors",
        "description": "Contains deliberate syntax errors: missing expression in 'int x = ;', missing closing paren, and invalid identifier token.",
        "expectedOutcome": "Syntax Error: Panic-mode recovery synchronizes and reports multiple errors with caret pointers."
    },
    "error_recovery.lang": {
        "title": "Multi-Error Panic-Mode Recovery",
        "category": "Diagnostics & Errors",
        "description": "Contains multiple consecutive syntax errors; validates parser synchronization at semicolons and keywords.",
        "expectedOutcome": "Syntax Error: Parser reports >= 2 errors without crashing and yields a partial AST."
    },
    "semantic_errors.lang": {
        "title": "Two-Pass Semantic Error Suite",
        "category": "Diagnostics & Errors",
        "description": "Demonstrates all 6 semantic checks: undeclared variables, arity mismatch, undefined function, redeclaration, and orphaned return.",
        "expectedOutcome": "Semantic Warning/Error: Exactly 6 distinct semantic diagnostics identified with line and column coordinates."
    }
}

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def classify_token_type(type_name: str) -> str:
    """Classifies a token type into an intuitive category for UI highlighting."""
    if type_name.startswith("KW_"):
        return "Keyword"
    if type_name in ("INT_LIT", "FLOAT_LIT", "STRING_LIT", "KW_TRUE", "KW_FALSE"):
        return "Literal"
    if type_name == "IDENT":
        return "Identifier"
    if type_name in ("PLUS", "MINUS", "STAR", "SLASH", "PERCENT", "ASSIGN",
                     "EQ", "NEQ", "LT", "GT", "LTE", "GTE", "AND", "OR", "NOT"):
        return "Operator"
    if type_name in ("LPAREN", "RPAREN", "LBRACE", "RBRACE", "COMMA", "SEMI"):
        return "Delimiter"
    if type_name == "EOF":
        return "EOF"
    return "Other"

def extract_source_snippet(source: str, line: Optional[int], column: Optional[int]) -> str:
    """Generates an ASCII-art caret pointing at the exact line and column."""
    if not line or not source:
        return ""
    lines = source.splitlines()
    if 1 <= line <= len(lines):
        src_line = lines[line - 1]
        col_pos = max(0, (column or 1) - 1)
        caret = " " * col_pos + "^"
        return f"{src_line}\n{caret}"
    return ""

def format_error_dict(phase: str, err_type: str, severity: str,
                      message: str, line: Optional[int], column: Optional[int],
                      source: str) -> Dict[str, Any]:
    snippet = extract_source_snippet(source, line, column)
    return {
        "phase": phase,
        "type": err_type,
        "severity": severity,
        "line": line,
        "column": column,
        "message": message,
        "snippet": snippet,
        "display": f"[{phase.upper()}] Line {line or '?'}:{column or '?'}: {message}"
    }

# -----------------------------------------------------------------------------
# API ROUTES
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    """Serves the main AST Visualizer web application interface."""
    return render_template("index.html")

@app.route("/api/health", methods=["GET"])
def api_health():
    """Healthcheck and compiler version metadata."""
    return jsonify({
        "status": "healthy",
        "compiler_version": compiler.VERSION,
        "project": "AST Visualizer / Pretty Printer",
        "project_id": "M13",
        "course": "BCSE307 - Compiler Design",
        "team": "Team 16",
        "faculty": "Dr. Shalini L",
        "python_version": sys.version.split()[0]
    })

@app.route("/api/samples", methods=["GET"])
def api_samples():
    """Returns the library of 13 sample programs with full metadata and code."""
    samples_list = []
    for filename, code in compiler.SAMPLES.items():
        meta = SAMPLE_METADATA.get(filename, {
            "title": filename,
            "category": "General",
            "description": "Sample program for AST Visualizer.",
            "expectedOutcome": "Valid compilation"
        })
        samples_list.append({
            "id": filename.replace(".lang", ""),
            "filename": filename,
            "title": meta["title"],
            "category": meta["category"],
            "description": meta["description"],
            "expectedOutcome": meta["expectedOutcome"],
            "code": code
        })
    return jsonify({"samples": samples_list, "total": len(samples_list)})

@app.route("/api/samples/<sample_id>", methods=["GET"])
def api_get_sample(sample_id: str):
    """Returns a single sample by ID or filename."""
    fname = sample_id if sample_id.endswith(".lang") else f"{sample_id}.lang"
    if fname in compiler.SAMPLES:
        code = compiler.SAMPLES[fname]
        meta = SAMPLE_METADATA.get(fname, {})
        return jsonify({
            "filename": fname,
            "title": meta.get("title", fname),
            "category": meta.get("category", "General"),
            "description": meta.get("description", ""),
            "expectedOutcome": meta.get("expectedOutcome", ""),
            "code": code
        })
    return jsonify({"error": f"Sample '{sample_id}' not found"}), 404

@app.route("/api/compile", methods=["POST"])
def api_compile():
    """
    Main Compilation API Endpoint.
    Consumes source code, runs the real compiler pipeline:
      Source -> Lexer -> Parser (with panic-mode recovery) -> AST -> Semantic Analysis -> Multi-Format Outputs
    Returns structured results, exact diagnostics, tokens, AST, and metrics.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payload: expected a JSON object."}), 400
    source = data.get("source", "")
    
    if not isinstance(source, str):
        return jsonify({"error": "Invalid payload: 'source' must be a string."}), 400

    start_total_time = time.perf_counter()
    errors: List[Dict[str, Any]] = []
    serialized_tokens: List[Dict[str, Any]] = []
    token_histogram: Dict[str, int] = {}
    
    # ---------------------------------------------------------
    # STAGE 1 & 2: LEXICAL ANALYSIS
    # ---------------------------------------------------------
    lex_start = time.perf_counter()
    tokens = []
    lex_status = "ok"
    lex_details = ""
    
    try:
        lexer = compiler.Lexer(source)
        tokens = lexer.tokenize()
        lex_ms = (time.perf_counter() - lex_start) * 1000.0
        lex_details = f"{len(tokens)} tokens scanned in {lex_ms:.2f}ms"
        
        for i, tok in enumerate(tokens):
            cat = classify_token_type(tok.type.name)
            serialized_tokens.append({
                "index": i + 1,
                "type": tok.type.name,
                "value": str(tok.value) if tok.value is not None else "",
                "line": tok.line,
                "column": tok.column,
                "category": cat
            })
            token_histogram[tok.type.name] = token_histogram.get(tok.type.name, 0) + 1
            
    except compiler.LexError as e:
        lex_ms = (time.perf_counter() - lex_start) * 1000.0
        lex_status = "error"
        lex_details = e.message
        errors.append(format_error_dict("lexer", "LexError", "error", e.message, e.line, e.column, source))
        
        # Cannot proceed further if lexing fails
        total_ms = (time.perf_counter() - start_total_time) * 1000.0
        return jsonify({
            "success": False,
            "has_syntax_errors": False,
            "has_semantic_issues": False,
            "tokens": serialized_tokens,
            "ast_dict": None,
            "errors": errors,
            "outputs": {},
            "stats": {
                "source_chars": len(source),
                "source_lines": source.count("\n") + 1 if source else 0,
                "token_count": len(serialized_tokens),
                "node_count": 0,
                "ast_depth": 0,
                "statement_count": 0,
                "lex_ms": round(lex_ms, 3),
                "parse_ms": 0.0,
                "sem_ms": 0.0,
                "total_ms": round(total_ms, 3),
                "token_histogram": token_histogram
            },
            "pipeline": [
                {"stage": "source", "name": "Source Code", "status": "ok", "ms": 0, "details": f"{len(source)} characters"},
                {"stage": "lexer", "name": "Lexical Analysis", "status": "error", "ms": round(lex_ms, 3), "details": lex_details},
                {"stage": "parser", "name": "Syntax Analysis", "status": "skipped", "ms": 0, "details": "Skipped due to lexical error"},
                {"stage": "ast", "name": "AST Generation", "status": "skipped", "ms": 0, "details": "No AST generated"},
                {"stage": "semantic", "name": "Semantic Analysis", "status": "skipped", "ms": 0, "details": "Skipped"},
                {"stage": "outputs", "name": "Output Generation", "status": "skipped", "ms": 0, "details": "Skipped"}
            ]
        })

    # ---------------------------------------------------------
    # STAGE 3 & 4: SYNTAX ANALYSIS & AST GENERATION
    # ---------------------------------------------------------
    parse_start = time.perf_counter()
    parse_status = "ok"
    parse_details = ""
    ast = None
    parse_errors: List[compiler.ParseError] = []

    try:
        parser = compiler.Parser(tokens)
        ast, parse_errors = parser.parse_recovering()
        parse_ms = (time.perf_counter() - parse_start) * 1000.0
        
        if parse_errors:
            parse_status = "warning" if len(ast.statements) > 0 else "error"
            parse_details = f"{len(parse_errors)} syntax error(s) detected with panic-mode recovery"
            for pe in parse_errors:
                errors.append(format_error_dict("parser", "ParseError", "error", pe.message, pe.line, pe.column, source))
        else:
            parse_details = f"Parsed {len(ast.statements)} top-level statement(s) in {parse_ms:.2f}ms"
            
    except Exception as e:
        parse_ms = (time.perf_counter() - parse_start) * 1000.0
        parse_status = "error"
        parse_details = str(e)
        errors.append(format_error_dict("parser", "FatalParseError", "error", str(e), None, None, source))

    # Determine AST status
    has_ast = ast is not None and (len(ast.statements) > 0 or not parse_errors)
    ast_status = "ok" if (has_ast and not parse_errors) else ("warning" if has_ast else "error")
    ast_details = f"{ast.count_nodes()} node(s), depth {ast.depth()}" if has_ast else "No valid AST nodes"

    # ---------------------------------------------------------
    # STAGE 5: SEMANTIC ANALYSIS (TWO-PASS)
    # ---------------------------------------------------------
    sem_start = time.perf_counter()
    sem_status = "ok"
    sem_details = ""
    semantic_issues: List[compiler.SemanticIssue] = []

    if has_ast:
        try:
            analyzer = compiler.SemanticAnalyzer()
            semantic_issues = analyzer.analyze(ast)
            sem_ms = (time.perf_counter() - sem_start) * 1000.0
            
            if semantic_issues:
                sem_status = "warning"
                sem_details = f"{len(semantic_issues)} semantic issue(s) flagged"
                for si in semantic_issues:
                    errors.append(format_error_dict("semantic", si.type, si.severity, si.message, si.line, si.column, source))
            else:
                sem_details = f"0 issues: Program is semantically valid ({sem_ms:.2f}ms)"
        except Exception as e:
            sem_ms = (time.perf_counter() - sem_start) * 1000.0
            sem_status = "error"
            sem_details = str(e)
            errors.append(format_error_dict("semantic", "AnalyzerCrash", "error", str(e), None, None, source))
    else:
        sem_ms = 0.0
        sem_status = "skipped"
        sem_details = "Skipped because AST is incomplete or empty"

    # ---------------------------------------------------------
    # STAGE 6: OUTPUT GENERATION
    # ---------------------------------------------------------
    outputs_start = time.perf_counter()
    outputs: Dict[str, str] = {}
    outputs_status = "ok"
    outputs_details = ""

    if has_ast:
        try:
            outputs["tree"] = compiler.TextTreePrinter().render(ast)
            outputs["sexpr"] = compiler.SExprPrinter().render(ast)
            outputs["json"] = compiler.JSONPrinter().render(ast)
            outputs["dot"] = compiler.GraphvizVisualizer().to_dot(ast, title="AST")
            outputs["html"] = compiler.HTMLVisualizer().render(ast, title="AST Visualizer & Explorer", source=source)
            outputs_ms = (time.perf_counter() - outputs_start) * 1000.0
            outputs_details = f"Generated 5 formats in {outputs_ms:.2f}ms"
        except Exception as e:
            outputs_status = "error"
            outputs_details = f"Render error: {e}"
            outputs["tree"] = f"Rendering error: {e}"
    else:
        outputs_status = "skipped"
        outputs_details = "Outputs unavailable for unparseable input"

    total_ms = (time.perf_counter() - start_total_time) * 1000.0

    # Clean AST dictionary for frontend visualizers
    ast_dict = ast.to_dict() if has_ast else None

    # Pipeline summary list
    pipeline = [
        {"stage": "source", "name": "Source Code", "status": "ok", "ms": 0, "details": f"{len(source)} chars, {source.count(chr(10)) + 1} lines"},
        {"stage": "lexer", "name": "Lexical Analysis", "status": lex_status, "ms": round(lex_ms, 3), "details": lex_details},
        {"stage": "parser", "name": "Syntax Analysis", "status": parse_status, "ms": round(parse_ms, 3), "details": parse_details},
        {"stage": "ast", "name": "AST Generation", "status": ast_status, "ms": round(parse_ms, 3), "details": ast_details},
        {"stage": "semantic", "name": "Semantic Analysis", "status": sem_status, "ms": round(sem_ms, 3), "details": sem_details},
        {"stage": "outputs", "name": "Output Generation", "status": outputs_status, "ms": round((time.perf_counter() - outputs_start) * 1000.0, 3), "details": outputs_details}
    ]

    is_overall_success = (len(errors) == 0 and has_ast)

    return jsonify({
        "success": is_overall_success,
        "has_syntax_errors": len(parse_errors) > 0,
        "has_semantic_issues": len(semantic_issues) > 0,
        "tokens": serialized_tokens,
        "ast_dict": ast_dict,
        "errors": errors,
        "outputs": outputs,
        "stats": {
            "source_chars": len(source),
            "source_lines": source.count("\n") + 1 if source else 0,
            "token_count": len(serialized_tokens),
            "node_count": ast.count_nodes() if has_ast else 0,
            "ast_depth": ast.depth() if has_ast else 0,
            "statement_count": len(ast.statements) if has_ast else 0,
            "lex_ms": round(lex_ms, 3),
            "parse_ms": round(parse_ms, 3),
            "sem_ms": round(sem_ms, 3),
            "total_ms": round(total_ms, 3),
            "token_histogram": token_histogram
        },
        "pipeline": pipeline
    })

@app.route("/api/tests/run", methods=["POST"])
def api_run_tests():
    """
    Executes the real 39-case test harness and 52-program corpus test from code.py.
    Intercepts stdout, parses every test case, and returns structured results.
    """
    start_time = time.perf_counter()
    old_stdout = sys.stdout
    sys.stdout = capture_buf = io.StringIO()
    
    passed_all = False
    try:
        passed_all = compiler.run_tests()
    except Exception as e:
        sys.stdout = old_stdout
        return jsonify({
            "success": False,
            "error": f"Test runner encountered an unhandled exception: {e}",
            "traceback": traceback.format_exc()
        }), 500
    finally:
        sys.stdout = old_stdout

    raw_output = capture_buf.getvalue()
    test_rows: List[Dict[str, Any]] = []

    # Parse stdout table into structured objects
    for line in raw_output.splitlines():
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("Test Case") or line_clean.startswith("---") or line_clean.startswith("TOTAL:"):
            continue
        parts = line_clean.split()
        if len(parts) >= 2 and parts[1] in ("PASS", "FAIL"):
            name = parts[0]
            status = parts[1]
            details = " ".join(parts[2:])
            category = name.split(".")[0] if "." in name else "general"
            test_rows.append({
                "name": name,
                "category": category,
                "status": status,
                "details": details
            })

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    passed_count = sum(1 for t in test_rows if t["status"] == "PASS")
    failed_count = sum(1 for t in test_rows if t["status"] == "FAIL")

    return jsonify({
        "success": passed_all,
        "total_tests": len(test_rows),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "elapsed_ms": round(elapsed_ms, 2),
        "tests": test_rows,
        "raw_output": raw_output
    })

@app.route("/api/diff", methods=["POST"])
def api_diff():
    """
    Compares the ASTs of two source code versions (sourceA and sourceB).
    Returns node count diff, depth diff, and side-by-side text tree comparison.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payload: expected a JSON object."}), 400
    src_a = data.get("sourceA", "")
    src_b = data.get("sourceB", "")
    if not isinstance(src_a, str) or not isinstance(src_b, str):
        return jsonify({"error": "Invalid payload: 'sourceA' and 'sourceB' must be strings."}), 400

    def compile_for_diff(src: str):
        try:
            toks = compiler.Lexer(src).tokenize()
            ast, errs = compiler.Parser(toks).parse_recovering()
            tree = compiler.TextTreePrinter().render(ast) if ast else "No AST"
            return {
                "nodes": ast.count_nodes() if ast else 0,
                "depth": ast.depth() if ast else 0,
                "tokens": len(toks),
                "errors": len(errs),
                "tree": tree,
                "ast_dict": ast.to_dict() if ast else None
            }
        except Exception as e:
            return {
                "nodes": 0, "depth": 0, "tokens": 0, "errors": 1,
                "tree": f"Error: {e}", "ast_dict": None
            }

    res_a = compile_for_diff(src_a)
    res_b = compile_for_diff(src_b)

    return jsonify({
        "versionA": res_a,
        "versionB": res_b,
        "diff": {
            "node_delta": res_b["nodes"] - res_a["nodes"],
            "depth_delta": res_b["depth"] - res_a["depth"],
            "token_delta": res_b["tokens"] - res_a["tokens"]
        }
    })

# -----------------------------------------------------------------------------
# MAIN ENTRYPOINT FOR LOCAL RUN
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 70)
    print("AST Visualizer & Compiler Studio (M13 - Team 16 - BCSE307)".center(70))
    print(f"Server starting on http://localhost:{port}".center(70))
    print("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=False)
