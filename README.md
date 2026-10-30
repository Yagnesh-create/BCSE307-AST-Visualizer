# AST Visualizer & Compiler Studio (M13)
**Interactive Compiler Front-End, AST Explorer & Multi-Format Pretty Printer**

**Review 3 audit (19 October 2026):** Read [requirement coverage and changes](docs/REVIEW3_COMPLETION.md), [measured results](evidence/RESULTS.md), and [report/slide corrections](docs/REPORT_AND_SLIDE_CORRECTIONS.md). The original Word/PowerPoint files need those corrections before submission. Review 2 acceptance, repository history and individual authorship remain unverified.

> **Course:** BCSE307 — Compiler Design (Winter Semester 2025–2026)  
> **Evaluation:** Review 3 — Final Project Demonstration  
> **Project ID:** M13 | **Team:** Team 16  
> **Evaluator / Faculty:** Dr. Shalini L, School of Computer Science and Engineering (SCOPE), VIT Vellore  

---

## 1. Project Overview & Problem Statement
This educational compiler front end exposes how source text becomes an AST. It accepts a C-like language with primitive type annotations and limited semantic checks. Complete static type checking and program execution are outside its scope.

The system performs:
1. **Lexical Analysis:** Single-pass scanning with 1-character lookahead and exact line/column tracking.
2. **Syntax Analysis:** Recursive-descent parsing with layered operator precedence and **Panic-Mode Error Recovery**.
3. **AST Generation:** An object-oriented Abstract Syntax Tree hierarchy.
4. **Two-Pass Semantic Analysis:** Scoped symbol tables enforcing variable declarations, scope shadowing, function call arity, and orphan return checks.
5. **Multi-Format Pretty Printing:** Decoupled Visitor Pattern generating Indented Text Trees, LISP S-expressions, JSON ASTs, Graphviz DOT digraphs, and Interactive HTML Explorers.
6. **Interactive Web Studio:** A web application (Flask + Vanilla HTML/CSS/JS) featuring graphical zoomable/pannable trees, token explorers, diagnostics with source caret pointers, live profiling, and automated test execution.

---

## 2. Team Members & Technical Ownership Matrix

| Member | Registration No. | Primary Technical Ownership | Core Modules & Evidence | Viva Topic |
|---|---|---|---|---|
| **Sourav S** | `24BKT0028` | Output Layer, HTML Explorer, Documentation | `HTMLVisualizer`, `TextTreePrinter`, `DEMO_GUIDE.md` | Tree Traversal, Visitor Pattern, HTML AST |
| **Ram Yadav** | `24BAI0201` | Custom Scanner & Tokenization Engine | `Lexer`, `Token`, `TokenType`, Lexer Unit Tests | Lookahead, String Escapes, State Machines |
| **Yagnesh Reddy** | `24BCE0886` | Parser, AST Hierarchy, Semantic Analysis | `Parser`, `Node`, `SemanticAnalyzer`, Panic Recovery | Recursive Descent, Scoping, Synchronization |
| **Sameep** | `24BCE2888` | CLI Engine, Profiler, Graphviz, Tests | `main()`, `Stats`, `GraphvizVisualizer`, Test Harness | CLI Pipeline, Profiling, Automated Testing |

---

## 3. Technology Stack & Architecture

- **Backend / Core Engine:** Pure Python 3.7+ (`code.py`, zero external dependencies for CLI; Flask for web API).
- **Web API Server:** Python + Flask (`server.py`).
- **Frontend UI:** Vanilla HTML5, modern CSS3 (custom dark developer-tool design system), and Vanilla JavaScript (`app.js`).
- **Zero Heavy Frameworks:** No React, Node.js build steps, or external database required. Clean, student-explainable architecture.

```text
Source Code (.lang)
       ↓
Lexical Analyzer (Scanner) ──▶ Structured Tokens [(type, value, line, col), ...]
       ↓
Recursive-Descent Parser   ──▶ Panic-Mode Recovery (synchronizes at ';' or keywords)
       ↓
Abstract Syntax Tree (AST) ──▶ Object-Oriented Nodes (Program, Stmt, Expr, Op)
       ↓
Two-Pass Semantic Analyzer ──▶ Pass 1: Function Hoisting | Pass 2: Scoped Symbol Resolution
       ↓
Visitor Pattern Renderers  ──▶ Text Tree, S-Expr, JSON AST, Graphviz DOT, Interactive HTML
```

---

## 4. Supported Custom Language Grammar (EBNF)

```ebnf
Program         ::= Statement* EOF
Statement       ::= FunctionDecl | VarDecl | IfStmt | WhileStmt | ForStmt | ReturnStmt | Block | ExprStmt

FunctionDecl    ::= ( "func" | Type ) IDENT "(" [ ParamList ] ")" Block
ParamList       ::= Param ( "," Param )*
Param           ::= [ Type ] IDENT

VarDecl         ::= ( "let" | Type ) IDENT [ "=" Expression ] ";"
VarDeclNoSemi   ::= ( "let" | Type ) IDENT [ "=" Expression ]
empty           ::= /* no tokens */
Type            ::= "int" | "float" | "bool" | "string" | "void"

IfStmt          ::= "if" "(" Expression ")" Block [ "else" ( IfStmt | Block ) ]
WhileStmt       ::= "while" "(" Expression ")" Block
ForStmt         ::= "for" "(" ( VarDeclNoSemi | Assignment | Expression | empty ) ";"
                              [ Expression ] ";"
                              ( Assignment | Expression | empty ) ")" Block

ReturnStmt      ::= "return" [ Expression ] ";"
Block           ::= "{" Statement* "}"
ExprStmt        ::= ( Assignment | Expression ) ";"
Assignment      ::= IDENT "=" Expression

Expression      ::= LogicalOr
LogicalOr       ::= LogicalAnd ( "||" LogicalAnd )*
LogicalAnd      ::= Equality ( "&&" Equality )*
Equality        ::= Relational ( ( "==" | "!=" ) Relational )*
Relational      ::= Additive ( ( "<" | "<=" | ">" | ">=" ) Additive )*
Additive        ::= Multiplicative ( ( "+" | "-" ) Multiplicative )*
Multiplicative  ::= Unary ( ( "*" | "/" | "%" ) Unary )*
Unary           ::= ( "-" | "!" ) Unary | Postfix
Postfix         ::= Primary ( "(" [ ArgList ] ")" )*
ArgList         ::= Expression ( "," Expression )*
Primary         ::= INT_LIT | FLOAT_LIT | STRING_LIT | BOOL_LIT | IDENT | "(" Expression ")"
```

---

## 5. Quickstart & Installation

### Step 1: Install Dependencies
Python 3.13 was verified in this audit. Install the recorded web dependencies:
```bash
python -m pip install -r requirements-review3.txt
```

### Step 2: Launch the Web Application
```bash
python server.py
```
Open your browser and navigate to:
**`http://localhost:5000`**

### Step 3: Run the Command-Line Interface (CLI)
The original CLI remains 100% functional with zero external dependencies:
```bash
# Print Unicode indented text tree (default)
python code.py samples/demo.lang

# Inspect lexical tokens
python code.py --tokens samples/demo.lang

# Generate LISP-style S-Expressions
python code.py --sexpr samples/demo.lang

# Export serialized JSON AST
python code.py --json samples/demo.lang

# Generate Graphviz DOT digraph
python code.py --dot samples/demo.lang

# Generate self-contained interactive HTML file
python code.py --html samples/demo.lang > tree.html

# Run semantic analysis diagnostic report
python code.py --analyze samples/semantic_errors.lang

# Display performance profiling and token histogram
python code.py --stats samples/demo.lang

# Execute the 39-case automated test harness & 52-corpus test
python code.py --test
```

---

## 6. Web Studio Features

1. **Interactive Code Editor:**
   - Synchronized line numbers, cursor position tracking (`Ln`, `Col`), indentation handling (Tab / Shift+Tab), and keyboard shortcut `Ctrl+Enter` to compile.
   - Sample program picker loading all 13 verified `.lang` sample files.
2. **Visual Compiler Pipeline Ribbon:**
   - Real-time display of the 6 stages: Source Code, Lexer, Parser, AST, Semantics, Output Formats.
   - Precise sub-millisecond execution timings and status pills (`Success`, `Warning`, `Error`).
3. **AST Visualizer Studio:**
   - **Mode A (Graphical Tree):** Interactive SVG canvas with zoom, pan, fit-to-view, and bezier curves connecting color-coded node categories.
   - **Mode B (Collapsible Cards):** Expandable/collapsible nested card tree with category tags and child counters.
   - **Node Inspector Drawer:** Click any node to inspect Class, Category, Atoms, Subtree count, Depth, Location, and JSON snippet, with a "Jump to Line in Editor" button.
4. **Token Explorer:**
   - Filterable, searchable table displaying Index, Token Type, Category badge, Lexeme value, and Coordinates (`Line:Col`).
5. **Diagnostics & Error Analysis:**
   - Categorized diagnostics with phase tags (`[LEXER]`, `[PARSER]`, `[SEMANTIC]`), severity, and source code snippet with exact `^` caret indicator pointing to the offending character.
   - Panic-Mode Recovery banner explaining parser synchronization.
6. **AST Output Formats:**
   - Tabs for Indented Text Tree, LISP S-Expression, JSON AST, Graphviz DOT, and Interactive HTML Preview.
   - One-click "Copy to Clipboard" and "Download File" buttons.
7. **Statistics Dashboard:**
   - Node count, AST depth, token count, execution time, and proportional front-end phase timing bars.
   - Token frequency distribution table and percentage bars.
8. **Sample Program Library:**
   - Filterable cards for all 13 `.lang` corpus files with expected outcomes and "Load into Playground & Run" actions.
9. **Presentation Workspace:**
   - Expand the workspace for demonstrations, navigate results through clickable pipeline stages, and export the complete AST as an SVG image for reports. Includes a category legend, compilation verdict, live metrics, and reduced-motion controls.
10. **Automated Validation Suite:**
    - Live browser test runner executing all 39 test assertions and reporting a 100% pass rate.
11. **AST Diff Viewer:**
    - Side-by-side comparison modal analyzing two source codes and calculating delta in nodes, depth, and tokens.

---

## 7. REST API Endpoints

- `GET /` — Serves the AST Visualizer Single Page Application.
- `GET /api/health` — Backend health status, compiler version, and team information.
- `GET /api/samples` — Returns metadata, description, expected outcome, and source for all 13 `.lang` samples.
- `GET /api/samples/<id>` — Returns a specific sample by filename.
- `POST /api/compile` — Primary compilation endpoint; accepts `{ "source": "..." }`, runs full pipeline, and returns tokens, AST dictionary, diagnostics, output formats, statistics, and pipeline status.
- `POST /api/tests/run` — Executes `compiler.run_tests()` and returns structured results for all 39 unit tests and corpus.
- `POST /api/diff` — Compares two source programs `{ "sourceA": "...", "sourceB": "..." }` and returns AST metrics and side-by-side text trees.

---

## 8. License & Academic Attribution
Developed for academic submission under the guidance of Dr. Shalini L, SCOPE, VIT Vellore.
Code is provided under the MIT License for educational and research purposes. See [LICENSE](LICENSE) and [Review3_Report.pdf](Review3_Report.pdf) for complete architectural specifications, algorithm proofs, and formal references.

## 9. Review 3 Verification & Packaging

```bash
python scripts/verify_review3.py
python scripts/package_review3.py
```

The verifier saves full expected/actual results, 30 additional integration/regression checks and repeated benchmarks in `evidence/`, and exits nonzero on failure. The package script creates `submission/Review3_Package.zip` and a SHA-256 inventory. The web test button runs only the original core suite. Recorded pass rates are not guarantees for all future inputs.

For an isolated Windows installation, run `python -m venv .venv`, then `.venv\Scripts\python.exe -m pip install -r requirements-review3.txt` and `.venv\Scripts\python.exe scripts/verify_review3.py`. The original `requirements.txt` remains a flexible Flask declaration. The snapshot records installed versions, with pip resolving platform-specific dependencies.

No repository URL or Git history was present in the supplied folder. Provide the genuine repository and contribution evidence before submission. The three added sample files are CLI/manual-paste examples; the browser picker retains its original 13 built-in samples.
