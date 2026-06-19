---
name: application-review
description: This skill should be used when the user asks to "run an application review", "review the application", "perform an application review", "audit the codebase", "/application-review", or otherwise requests a comprehensive code-quality and security review of the project in the current working directory delivered as a PDF report named application-review.PDF.
version: 1.0.0
---

# Application Review

Perform a comprehensive review of the project in the current working directory and produce `application-review.PDF` in the docs/ directory. The review covers application functions, code quality (with pylint), obsolete libraries, security vulnerabilities, unit-test state, and prioritized improvement suggestions.

## Scope

Analyze only the files in the `python/` directory.

Also, **ignore** these subdirectories in the `python/` directory.

- `dbx/`
- `docs/`

Focus analysis on:

- `python/core/` — Django application code
- `python/plog/` — Django configuration files
- `python/src/` — Non-Django application code
- `python/tests/` — test suite
- `python/main.py` — CLI entry points and top-level scripts
- `python/*.sh`, `python/*.ps1` — build/run scripts
- `pyproject.toml`

## Workflow

Execute the steps below in order. Do not skip steps.

### Step 1 — Inventory the project

Use Glob and Read to enumerate the directories above. Build a mental map of:

- Entry points (CLI scripts, Django commands, `main.py`)
- Python modules
- Configuration files and dependency declarations

### Step 2 — Analyze each category

Produce findings for every category. Each category becomes a section in the PDF.

**a. Application Functions**
Describe the one-to-many primary functions of the application. For each major module or entry point, briefly describe its purpose, inputs, and outputs. Aim for breadth over depth — every entry point and major module should be mentioned.

**b. Code Quality**
Rate overall code quality as **LOW**, **MEDIUM**, or **HIGH** with justification. Consider naming conventions, modularity, separation of concerns, docstrings, error handling, and code duplication.

- Detect duplicate methods/functions: scan for repeated `def name(` declarations across files and for near-identical bodies.
- Detect long functions: flag any function whose body exceeds 40 lines (excluding blank lines and the `def` line).
- Run pylint and capture both the score and the top issue categories:

  ```bash
  cd python && ./tests.sh
  ```

Record the numeric score and the rating separately so both appear in the PDF.

**c. Obsolete or Problematic Libraries**
Inspect `python/pyproject.toml` and cross-check with the output of `uv pip list`.

Also check the dependency graph, the out of `uv tree`.

Flag libraries that are:
- Deprecated or end-of-life
- Superseded by better-maintained alternatives
- Pinned to outdated versions with known issues
- Unmaintained (no release in 2+ years)
- Have only 1 or 2 contributors


**d. Security Vulnerabilities**
Identify concerns including:

- Hardcoded secrets, API keys, connection strings, or credentials
- Use of `eval()`, `exec()`, `pickle.loads`, or `subprocess` with `shell=True`
- Insecure defaults (SSL verification disabled, permissive CORS, debug mode in prod)
- Overly broad `except:` / `except Exception:` that swallow errors
- Path-traversal or injection risks in file/URL handling
- Known-vulnerable dependency versions (call out CVEs only when confident)

Use `grep` for fast scanning, e.g. `grep -rnE 'eval\(|exec\(|shell=True|verify=False' python/src python/*.py`.

**e. Unit Test State and Completeness**
Review `python/tests/` and `python/pytest.ini`. Comment on:

- Coverage breadth — which `src/` modules have corresponding tests, which don't
- Test quality — meaningful assertions vs. smoke tests
- Use of mocks vs. live services
- Missing tests for critical paths (entry points, error handling, edge cases)

If `pytest-cov` is configured, optionally report coverage:

```bash
cd python && uv run pytest --cov=src --cov-report=term 2>&1 | tail -30
```

**f. Suggestions for Improvement**
Provide concrete, prioritized suggestions across:

- Design — module boundaries, abstractions, configuration handling
- Code quality — duplication removal, function decomposition, type hints, docstrings
- Tests — coverage gaps, fixtures, parametrization, mocking strategy

Order each list highest-impact first.

### Step 3 — Assemble findings JSON

Write the analysis to a temporary findings file at `python/tmp/application-review-findings.json` matching the structure in `references/findings-template.json`. The PDF script consumes this file. Create the `python/tmp/` directory if it does not exist.

### Step 4 — Generate the PDF

Run the bundled script (no copying — invoke it from its skill location so the skill stays self-contained):

```bash
cd /Users/cjoakim/github/cj-claude-xml && \
  uv --project python run python .claude/skills/application-review/scripts/gen_review_pdf.py \
    --findings python/tmp/application-review-findings.json \
    --output application-review.PDF
```

If `reportlab` is not installed, the script prints an install instruction and exits non-zero. Install it with:

```bash
cd python && uv add reportlab
```

then retry the command above.

The PDF must be written to the **project root** as `application-review.PDF` (uppercase extension as specified). Confirm the file exists and report its size.

### Step 5 — Cleanup

Delete `python/tmp/application-review-findings.json` after the PDF is generated successfully. Do not delete the bundled script in `.claude/skills/application-review/scripts/`.

## Bundled Resources

### Scripts

- **`scripts/gen_review_pdf.py`** — reportlab-based generator. Reads a JSON findings file, writes a PDF with title page, table of contents, and one section per category (a–f). Handles missing `reportlab` gracefully.

### References

- **`references/findings-template.json`** — exact JSON schema the PDF script expects. Populate every field; use empty arrays for categories with no findings rather than omitting keys.

## Output Requirements

- File name: `application-review.pdf`
- Location: project root
- Contents: title page, table of contents, sections a–f, each clearly labeled
- Code-quality rating and pylint rating must both appear, distinctly labeled
