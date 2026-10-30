# Measured Review 3 results

Run timestamp (UTC): 2026-10-30T14:06:46.372784+00:00
Environment: Python 3.13.15, Flask 3.1.3, Windows-11-10.0.26200-SP0.

Core suite: PASS (see unit_tests.txt and core_results.json).
Integration/regression: 30/30 passed.

| Test | Expected | Actual | Result |
|---|---|---|---|
| web.home | 200 | 200 | PASS |
| web.health | 200 | 200 | PASS |
| web.missing_sample | 404 | 404 | PASS |
| valid.all_output_formats | ['dot', 'html', 'json', 'sexpr', 'tree'] | ['dot', 'html', 'json', 'sexpr', 'tree'] | PASS |
| valid.semantic_program | True | True | PASS |
| boundary.empty_program | True | True | PASS |
| regression.comments_only | True | True | PASS |
| boundary.20_parentheses | True | True | PASS |
| stress.1000_statements | 1000 | 1000 | PASS |
| invalid.lexical | lexer | lexer | PASS |
| invalid.syntax | True | True | PASS |
| invalid.semantic | True | True | PASS |
| regression.unmatched_closing_brace | True | True | PASS |
| regression.partial_ast | 2 | 2 | PASS |
| failure./api/compile.non_object.[1] | 400 | 400 | PASS |
| failure./api/compile.non_object.'text' | 400 | 400 | PASS |
| failure./api/compile.non_object.12 | 400 | 400 | PASS |
| failure./api/compile.non_object.None | 400 | 400 | PASS |
| failure./api/compile.malformed_json | 400 | 400 | PASS |
| failure./api/diff.non_object.[1] | 400 | 400 | PASS |
| failure./api/diff.non_object.'text' | 400 | 400 | PASS |
| failure./api/diff.non_object.12 | 400 | 400 | PASS |
| failure./api/diff.non_object.None | 400 | 400 | PASS |
| failure./api/diff.malformed_json | 400 | 400 | PASS |
| failure.source_type | 400 | 400 | PASS |
| failure.diff_source_type | 400 | 400 | PASS |
| failure.request_size_limit | 413 | 413 | PASS |
| diff.equal_sources | 0 | 0 | PASS |
| regression.deterministic_json | True | True | PASS |
| failure.cli_missing_file | True | True | PASS |

## Benchmark method

Three warmups and 20 measured repetitions per input size. Each input declares unique integer variables. Times cover in-process lexing, strict parsing and semantic analysis only. They exclude process startup, rendering, HTTP transport and browser layout. These are measurements on this machine, not guaranteed limits or a comparison with another compiler.

| Statements | Tokens | AST nodes | Median ms | Min ms | Max ms |
|---|---|---|---|---|---|
| 10 | 51 | 21 | 0.5246 | 0.1307 | 0.7173 |
| 100 | 501 | 201 | 4.1336 | 1.5023 | 5.4892 |
| 1000 | 5001 | 2001 | 43.4366 | 30.4211 | 54.321 |

Increasing input size also increases work. Small timing differences are sensitive to interpreter state and background processes. The 52-program corpus tests syntax acceptance only; it does not prove all programs pass semantic analysis. API tests use Flask's in-process client and do not verify browser interactions.
