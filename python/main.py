"""
Usage:
uv run main.py claude_telemetry_extract
"""

import json
import logging
import sys
import traceback

from docopt import docopt
from dotenv import load_dotenv

from src.io.fileio import FileIO

# Chris Joakim, 2026


def print_options(msg):
    logging.warning(msg)
    arguments = docopt(__doc__, version="1.0.0")
    logging.warning(arguments)


def claude_telemetry_extract() -> None:
    pass


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
            else:
                print_options("Error: invalid function: {}".format(func))
    except Exception as e:
        logging.warning(str(e))
        logging.warning(traceback.format_exc())
