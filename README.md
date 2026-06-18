# claude-code-telemetry

POC on how to extract Claude Code usage from the various ~./claude/ files 
and emit telemetry to OTEL/Azure.

## The Problem to Solve

- Claude Code is an excellent AI tool/assistant
- However, it provides little insight into when it calls LLM(s) and the token utilization
- It provides little insight on how/when/if Skills and Sub-agents are called

### Solution Goals

- Collecting this telemetry either locally, or to Azure
- Utilize the OpenTelemetry (OTEL) standard API

### Solutions in this Repo

This repo explores two ways to solve this problem:
- 1. Per the Claude Code documentation
- 2. With a custom solution

---

## Part 1 : Implementing OpenTelemetry (OTEL) per the Claude Code Documentation

See https://code.claude.com/docs/en/monitoring-usage

### Localhost OpenTelemetry Docker Container

See https://opentelemetry.io/docs/collector/quick-start/


### Environment Variables

Per the above Claude documentation, set these environment variables on your system.

```
CLAUDE_CODE_ENABLE_TELEMETRY=1
CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_LOG_USER_PROMPTS=1
OTEL_LOGS_EXPORT_INTERVAL=5000
OTEL_LOGS_EXPORTER=otlp
OTEL_METRICS_EXPORT_INTERVAL=10000
OTEL_METRICS_EXPORTER=otlp
OTEL_TRACES_EXPORT_INTERVAL=10000
OTEL_TRACES_EXPORTER=otlp
```

Docs
```
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer your-token"
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_LOGS_EXPORT_INTERVAL=5000     # 5 seconds (default: 5000ms)
export OTEL_LOGS_EXPORTER=otlp          # Options: otlp, console, none
export OTEL_METRIC_EXPORT_INTERVAL=10000  # 10 seconds (default: 60000ms)
export OTEL_METRICS_EXPORTER=otlp       # Options: otlp, prometheus, console, none
```



### Alternative Localhost Implementation with the Jaeger Container

- Links
  - https://www.jaegertracing.io/
  - https://www.jaegertracing.io/docs/2.19/


---

## Part 2: Emitting Custom Telemetry with Python

- Claude Code writes local files to the ~/.claude/ directory as it executes
  - This directory structure doesn't seem to be documented
