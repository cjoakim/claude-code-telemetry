# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo explores how to capture Claude Code usage telemetry via OpenTelemetry (OTEL). Three solutions are implemented:
1. **Solution 1**: Route OTEL to a localhost Docker container (standard OTEL collector or Jaeger)
2. **Solution 2**: Route OTEL to Azure Application Insights (requires Microsoft Entra auth — deferred)
3. **Solution 3**: Custom Python script that reads `~/.claude/history.jsonl` and session files directly

## Environment Variables (Solutions 1 & 2)

Set these before starting Claude Code to enable telemetry emission:

```
CLAUDE_CODE_ENABLE_TELEMETRY=1
CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_LOG_USER_PROMPTS=1
OTEL_LOGS_EXPORTER=otlp
OTEL_METRICS_EXPORTER=otlp
OTEL_TRACES_EXPORTER=otlp
```

For Solution 3, set `APPLICATIONINSIGHTS_CONNECTION_STRING` and optionally use `python/.env`.

## Docker Commands

```bash
# Standard OTEL collector (outputs to otel-logs/telemetry.jsonl)
docker compose -f otel-compose.yml up
docker compose -f otel-compose.yml down

# Jaeger (UI at http://localhost:16686)
docker compose -f jaeger-compose.yml up
docker compose -f jaeger-compose.yml down
```

## Python Solution (Solution 3)

All Python work lives in the `python/` directory. Requires **Python 3.13** and **uv**.

### Setup

```bash
cd python
./venv.sh          # macOS/Linux — creates .venv and installs dependencies
# or
.\venv.ps1         # Windows

source .venv/bin/activate
```

### Running

```bash
uv run main.py claude_telemetry_extract
uv run main.py zip_claude_directory <directory>
uv run main.py zip_claude_directory ~/github/some-repo/.claude
```

`claude_telemetry_extract` reads `~/.claude/history.jsonl`, finds new events since the last run, loads the matching session JSONL files from `~/.claude/projects/`, filters to events with model usage, and writes JSON output to `~/claudelog/data/telemetry_<timestamp>.json`.

`zip_claude_directory` zips the `agents/`, `commands/`, `hooks/`, `skills/` subdirs plus `settings*.json` from the given `.claude` directory into `python/tmp/<basename>.zip`.

### Linting & Formatting

```bash
cd python
./code-reformat.sh    # runs ruff format then pylint --errors-only
```

Line length: 100 (ruff), 120 (pylint).

### Tests

```bash
cd python
uv run pytest
```

## Code Architecture

### Python package layout (`python/src/`)

- `aitools/claude_telemetry_util.py` — `ClaudeTelemetryUtil`: reads `~/.claude/history.jsonl`, finds new events by timestamp watermark (stored in `~/claudelog/history_timestamp.txt`), loads session JSONL files, deduplicates by UUID, filters to events with model usage, traverses parent event chains, writes JSON output
- `aitools/claude_zip_util.py` — `ClaudeZipUtil`: zips a `.claude` directory's configuration subdirs into `python/tmp/`
- `io/fileio.py` — `FileIO`: static utility class for reading/writing text, JSON, CSV files

### Claude data sources

`~/.claude/history.jsonl` — one JSON record per line; each has `timestamp` (epoch ms), `project` (absolute path), and `sessionId`.

`~/.claude/projects/<path-encoded-project>/` — directory named by replacing `/` with `-` in the project path; contains per-session JSONL files named `<sessionId>*.jsonl`, each with individual Claude interaction events including model, token counts, and parent/child UUID chains.

### Telemetry filtering logic

`ClaudeTelemetryUtil.filter_captured_telemetry()` keeps only events where `event["message"]["model"]` exists, then walks `parentUuid` chains to attach ancestor context. This means the output focuses on LLM API calls rather than all Claude Code events.

### Docker configuration

- `otel-compose.yml` + `otel-collector-config.yml`: OTEL collector on ports 4317 (gRPC) and 4318 (HTTP); writes `otel-logs/telemetry.jsonl` with 100 MB rotation
- `jaeger-compose.yml`: Jaeger all-in-one on ports 4317, 4318, and 16686 (UI)
