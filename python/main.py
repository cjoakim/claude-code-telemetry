"""
CLI entry point for Claude Code telemetry extraction, OTEL export, and .claude packaging.

Dispatches on sys.argv[1] to extract telemetry from ~/.claude, emit spans to Azure
or a local OTEL collector, or zip a .claude directory for portability.

Usage:
uv run main.py claude_telemetry_extract --shallow
uv run main.py claude_telemetry_extract --deep
uv run main.py claude_telemetry_extract --deep --since <epoch>
uv run main.py claude_telemetry_extract --deep --since 1781807840000
uv run main.py claude_telemetry_extract --hooks  # TODO implement
uv run main.py emit_otel_telemetry ~/.claudex/data/telemetry_1781981432702.json --azure
uv run main.py emit_otel_telemetry ~/.claudex/data/telemetry_1781981432702.json --local
uv run main.py emit_otel_telemetry ~/.claudex/data/telemetry_1781981432702.json --azure --local
uv run main.py zip_claude_directory <directory>
uv run main.py zip_claude_directory ~/some/path/.claude

Chris Joakim, 2026
"""

import logging
import os
import sys
import traceback

from docopt import docopt
from dotenv import load_dotenv

from src.aitools.claude_telemetry_util import ClaudeTelemetryUtil
from src.aitools.claude_zip_util import ClaudeZipUtil
from src.aitools.otel_emitter import OtelEmitter
from src.io.fileio import FileIO


def print_options(msg: str) -> None:
    """Log an error message and print docopt usage/help to the log."""
    logging.warning(msg)
    arguments = docopt(__doc__, version="1.0.0")
    logging.warning(arguments)


def claude_telemetry_extract() -> None:
    """
    Extract Claude Code telemetry and write JSON under ~/.claudex/data/.

    Mode is selected from sys.argv flags: --hooks (not implemented), --deep
    (include session JSONL events), or default shallow (history.jsonl only).
    """
    util = ClaudeTelemetryUtil()
    if "--hooks" in sys.argv:
        filename = util.capture_hooks()
        print(f"util.capture_hooks() -> {filename}")
    elif "--deep" in sys.argv:
        filename = util.capture_usage(deep=True)
        print(f"util.capture_usage(deep=True) -> {filename}")
    else:
        filename = util.capture_usage(deep=False)
        print(f"util.capture_usage(deep=False) -> {filename}")


def emit_otel_telemetry(telemetry_filename: str) -> None:
    """
    Read a telemetry JSON file and emit events to configured OTEL backends.

    Args:
        telemetry_filename: Path to JSON produced by claude_telemetry_extract.

    Backend flags (sys.argv): --azure for Application Insights, --local for
    localhost:4317 OTLP gRPC. Both may be specified in one run.
    """
    print("emit_otel_telemetry")
    emitter = OtelEmitter()
    telemetry_events: list[dict] = FileIO.read_json(telemetry_filename)

    if "--azure" in sys.argv:
        emitter.emit_to_azure_app_insights(telemetry_events)
    if "--local" in sys.argv:
        emitter.emit_to_localhost_collector(telemetry_events)


def zip_claude_directory(directory: str) -> None:
    """
    Create a portable zip of a .claude directory under python/tmp/.
    This demonstrates how portable the files are between projects.

    Args:
        directory: Path to the .claude directory to package.
    """
    util = ClaudeZipUtil()
    filename = util.zip_claude_directory(directory)
    print(f"util.zip_claude_directory() -> {filename}")


def init_logging() -> None:
    """Configure root logging with timestamped INFO-level output."""
    logging_format = "%(asctime)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=logging_format, datefmt="%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    try:
        init_logging()
        load_dotenv(override=True)
        if len(sys.argv) < 2:
            print_options("Error: no CLI args provided")
        else:
            func = sys.argv[1].lower()
            if func == "claude_telemetry_extract":
                claude_telemetry_extract()
            elif func == "emit_otel_telemetry":
                telemetry_filename = os.path.expanduser(sys.argv[2])
                emit_otel_telemetry(telemetry_filename)
            elif func == "zip_claude_directory":
                if len(sys.argv) < 3:
                    print_options("Error: zip_claude_directory requires a directory argument")
                else:
                    zip_claude_directory(sys.argv[2])
            else:
                print_options("Error: invalid function: {}".format(func))
    except Exception as e:
        logging.warning(str(e))
        logging.warning(traceback.format_exc())
