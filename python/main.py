"""
Usage:
uv run main.py claude_telemetry_extract --shallow
uv run main.py claude_telemetry_extract --deep
uv run main.py claude_telemetry_extract --hooks
uv run main.py zip_claude_directory <directory>
uv run main.py zip_claude_directory ~/some/path/.claude
"""

import json
import logging
import sys
import traceback

from docopt import docopt
from dotenv import load_dotenv

from src.aitools.claude_telemetry_util import ClaudeTelemetryUtil
from src.aitools.claude_zip_util import ClaudeZipUtil
from src.io.fileio import FileIO

# Chris Joakim, 2026


def print_options(msg):
    logging.warning(msg)
    arguments = docopt(__doc__, version="1.0.0")
    logging.warning(arguments)


def claude_telemetry_extract() -> None:
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


def zip_claude_directory(directory: str) -> None:
    """Create a portable zip file of the .claude directory to port to another repo."""
    util = ClaudeZipUtil()
    filename = util.zip_claude_directory(directory)
    print(f"util.zip_claude_directory() -> {filename}")


def init_logging() -> None:
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
