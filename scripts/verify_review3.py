"""Reproduce Review 3 checks and evidence: python scripts/verify_review3.py.

Uses the compiler's own tests plus HTTP contract and regression checks.
No running server is needed. Flask must be installed for integration tests.
"""
from pathlib import Path
import contextlib
import importlib.metadata
import io
import json
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server

core = server.compiler
OUT = ROOT / "evidence"
OUT.mkdir(exist_ok=True)
rows = []


def check(name, expected, function):
    try:
        actual = function()
        passed = actual == expected
    except Exception as exc:
        actual = f"{type(exc).__name__}: {exc}"
        passed = False
    rows.append(dict(test=name, expected=expected, actual=actual, passed=passed))


def main():
    rows.clear()
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        core_ok = core.run_tests()
    (OUT / "unit_tests.txt").write_text(capture.getvalue(), encoding="utf-8")
    # Preserve the full existing expected/actual values without console truncation.
    original_report = core.TestResult.report
    full_rows = []
    def record_report(result):
        full_rows.extend(dict(test=n, status=s, expected=e, actual=a)
                         for n, s, e, a in result.rows)
        return result.failed == 0
    try:
        core.TestResult.report = record_report
        core.run_tests()
    finally:
        core.TestResult.report = original_report
    (OUT / "core_results.json").write_text(json.dumps(full_rows, indent=2), encoding="utf-8")
    client = server.app.test_client()
    def compile_source(source):
        return client.post("/api/compile", json={"source": source}).get_json()
    check("web.home", 200, lambda: client.get("/").status_code)
    check("web.health", 200, lambda: client.get("/api/health").status_code)
    check("web.missing_sample", 404, lambda: client.get("/api/samples/not_found.lang").status_code)
    check("valid.all_output_formats", ["dot", "html", "json", "sexpr", "tree"],
          lambda: sorted(compile_source("let x = 1 + 2 * 3;")["outputs"]))
    check("valid.semantic_program", True, lambda: compile_source("func add(a,b) { return a+b; } let x=add(1,2);")["success"])
    check("boundary.empty_program", True, lambda: compile_source("")["success"])
    check("regression.comments_only", True, lambda: compile_source("// hello\n/* world */")["success"])
    check("boundary.20_parentheses", True, lambda: compile_source("let x=" + "("*20 + "1" + ")"*20 + ";")["success"])
    check("stress.1000_statements", 1000, lambda: compile_source("\n".join(f"let x{i}={i};" for i in range(1000)))["stats"]["statement_count"])
    check("invalid.lexical", "lexer", lambda: compile_source("let x=@;")["errors"][0]["phase"])
    check("invalid.syntax", True, lambda: compile_source("let x=;")["has_syntax_errors"])
    check("invalid.semantic", True, lambda: compile_source("let x=unknown;")["has_semantic_issues"])
    check("regression.unmatched_closing_brace", True, lambda: compile_source("}")["has_syntax_errors"])
    check("regression.partial_ast", 2, lambda: compile_source("let a=1; let bad=; let b=2;")["stats"]["statement_count"])
    for endpoint in ("/api/compile", "/api/diff"):
        for value in ([1], "text", 12, None):
            check(f"failure.{endpoint}.non_object.{value!r}", 400,
                  lambda endpoint=endpoint, value=value: client.post(endpoint, data=json.dumps(value), content_type="application/json").status_code)
        check(f"failure.{endpoint}.malformed_json", 400,
              lambda endpoint=endpoint: client.post(endpoint, data="{broken", content_type="application/json").status_code)
    check("failure.source_type", 400, lambda: client.post("/api/compile", json={"source": 3}).status_code)
    check("failure.diff_source_type", 400, lambda: client.post("/api/diff", json={"sourceA": []}).status_code)
    check("failure.request_size_limit", 413, lambda: client.post("/api/compile", json={"source": "a"*1048576}).status_code)
    check("diff.equal_sources", 0, lambda: client.post("/api/diff", json={"sourceA":"let a=1;", "sourceB":"let a=1;"}).get_json()["diff"]["node_delta"])
    check("regression.deterministic_json", True, lambda: compile_source("let x=2;")["outputs"]["json"] == compile_source("let x=2;")["outputs"]["json"])
    def cli_missing():
        result = subprocess.run([sys.executable, str(ROOT / "code.py"), "__missing_review3__.lang"], cwd=ROOT, capture_output=True, encoding="utf-8")
        return result.returncode == 1 and "cannot read" in result.stderr
    check("failure.cli_missing_file", True, cli_missing)

    benchmarks = []
    for size in (10, 100, 1000):
        source = "\n".join(f"let x{i}={i};" for i in range(size))
        for _ in range(3):
            core.parse_and_analyze(source)
        measurements = []
        for _ in range(20):
            start = time.perf_counter()
            ast, tokens, lex_ms, parse_ms, issues, sem_ms = core.parse_and_analyze(source)
            assert not issues
            measurements.append((time.perf_counter()-start)*1000)
        benchmarks.append(dict(statements=size, characters=len(source), tokens=len(tokens), nodes=ast.count_nodes(),
                               median_ms=round(statistics.median(measurements), 4), min_ms=round(min(measurements), 4), max_ms=round(max(measurements), 4), samples_ms=measurements))
    result = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                  platform=platform.platform(), flask=importlib.metadata.version("flask"),
                  core_passed=core_ok, integration_passed=sum(r["passed"] for r in rows),
                  integration_total=len(rows), cases=rows, benchmarks=benchmarks)
    (OUT / "review3_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = ["# Measured Review 3 results", "", f"Run timestamp (UTC): {result['recorded_at_utc']}",
             f"Environment: Python {result['python']}, Flask {result['flask']}, {result['platform']}.", "",
             f"Core suite: {'PASS' if core_ok else 'FAIL'} (see unit_tests.txt and core_results.json).",
             f"Integration/regression: {result['integration_passed']}/{len(rows)} passed.", "",
             "| Test | Expected | Actual | Result |", "|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['test']} | {row['expected']} | {row['actual']} | {'PASS' if row['passed'] else 'FAIL'} |")
    lines += ["", "## Benchmark method", "", "Three warmups and 20 measured repetitions per input size. Each input declares unique integer variables. Times cover in-process lexing, strict parsing and semantic analysis only. They exclude process startup, rendering, HTTP transport and browser layout. These are measurements on this machine, not guaranteed limits or a comparison with another compiler.", "", "| Statements | Tokens | AST nodes | Median ms | Min ms | Max ms |", "|---|---|---|---|---|---|"]
    for b in benchmarks:
        lines.append(f"| {b['statements']} | {b['tokens']} | {b['nodes']} | {b['median_ms']} | {b['min_ms']} | {b['max_ms']} |")
    lines += ["", "Increasing input size also increases work. Small timing differences are sensitive to interpreter state and background processes. The 52-program corpus tests syntax acceptance only; it does not prove all programs pass semantic analysis. API tests use Flask's in-process client and do not verify browser interactions."]
    (OUT / "RESULTS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    demo = (ROOT / "samples/demo.lang").read_text(encoding="utf-8")
    for mode, extension in (("tree","txt"),("json","json"),("dot","dot"),("html","html"),("tokens","tokens.txt"),("analyze","analyze.txt")):
        (OUT / f"demo.{extension}").write_text(core._render(demo, mode), encoding="utf-8")
    print(f"Core: {'PASS' if core_ok else 'FAIL'}; integration: {result['integration_passed']}/{len(rows)}. Evidence: {OUT}")
    for row in rows:
        if not row["passed"]:
            print("FAIL:", row)
    return 0 if core_ok and all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
