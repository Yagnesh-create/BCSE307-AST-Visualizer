# Test entry points

Run `python code.py --test` for the original 39 checks, including the 52-program syntax corpus.

Run `python scripts/verify_review3.py` for core expected/actual evidence, 30 additional integration/regression checks, stress coverage and benchmarks. Install web dependencies first. The script exits nonzero if a check fails and writes measured evidence under `evidence/`.

Coverage includes valid programs, syntax/semantic/lexical errors, empty/comment-only inputs, 20 nested parentheses, 1,000 declarations, unmatched braces, partial recovery, non-object/malformed JSON, invalid source types, request-size failure, a missing sample, a missing CLI file and deterministic output. It does not perform browser interaction testing.
