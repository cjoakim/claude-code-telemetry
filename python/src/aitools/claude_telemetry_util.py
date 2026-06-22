# Extract Claude Code usage telemetry from ~/.claude history and session JSONL files.
# Reads history.jsonl for new sessions, optionally loads per-session events, filters
# to model-usage events, and writes JSON output to ~/.claudex/data/.
# Chris Joakim, 2026

import getpass
import json
import os
import socket
import sys
import time
import traceback
from datetime import datetime, timezone
from typing import Any

from src.io.fileio import FileIO


class ClaudeTelemetryUtil:
    """Read Claude Code history and session files and export model-usage telemetry."""

    def __init__(self):
        """Initialize paths, timestamps, and the in-memory telemetry payload."""
        self.history_file = os.path.expanduser("~/.claude/history.jsonl")
        self.last_history_file = os.path.expanduser("~/.claudex/history_timestamp.txt")
        self.data_dir = os.path.expanduser("~/.claudex/data")
        self.prev_timestamp = 0
        self.curr_timestamp = int(time.time() * 1000)
        self.last_timestamp = 0
        self.data = dict()
        self.metadata = dict()
        self.telemetry_events = []
        self.data["metadata"] = self.metadata
        self.data["telemetry_events"] = self.telemetry_events
        self.user = getpass.getuser()

    def capture_usage(self, deep: bool = False) -> str | None:
        """
        Capture Claude telemetry events since the last recorded timestamp.

        Reads new entries from ~/.claude/history.jsonl. When deep is True, also
        loads matching session JSONL files from ~/.claude/projects/. Filters to
        events with model usage, writes JSON to ~/.claudex/data/, and updates the
        watermark file.

        Args:
            deep: When True, load per-session events for each new history entry.

        Returns:
            Path to the written JSON file, or None if nothing was captured.
        """
        try:
            self.prev_timestamp = self.read_last_history_timestamp()
            if "--since" in sys.argv:
                since_epoch = int(sys.argv[sys.argv.index("--since") + 1])
                if since_epoch > 0:
                    self.prev_timestamp = since_epoch
            self.metadata["prev_timestamp"] = self.prev_timestamp
            self.metadata["curr_timestamp"] = self.curr_timestamp
            self.metadata["hostname"] = socket.gethostname()

            if self.prev_timestamp > 0 and (self.curr_timestamp - self.prev_timestamp) < 10000:
                print("last run too recent")
                return None

            new_history_events = self.read_new_history_events()
            print(f"{len(new_history_events)} new_history_events since {self.prev_timestamp}")
            if len(new_history_events) == 0:
                print("no new history events")
                return None

            self.last_timestamp = self.prev_timestamp
            for event in new_history_events:
                try:
                    event_epoch = event["timestamp"]
                    if isinstance(event_epoch, int):
                        event["event_source"] = "history.jsonl"
                        self.telemetry_events.append(event)
                        if deep == True:
                            self.process_history_event(event)
                        self.last_timestamp = max(self.last_timestamp, event_epoch)
                except Exception as e:
                    print(traceback.format_exc())
            self.write_last_history_timestamp(self.last_timestamp)

            self.filter_captured_telemetry()
            outfile = os.path.join(self.data_dir, f"telemetry_{self.last_timestamp}.json")
            FileIO.write_json(self.data, outfile)
            print(
                f"ClaudeTelemetryUtil#capture_usage - wrote {len(self.telemetry_events)} telemetry events to {outfile}"
            )
            return outfile
        except Exception as e:
            print(f"Exception in ClaudeTelemetryUtil#capture_usage: {e}")
            print(traceback.format_exc())
            return None

    def capture_hooks(self) -> str | None:
        """Capture hook-related telemetry. Not yet implemented."""
        return ""  # TODO implement

    def read_new_history_events(self) -> list[dict]:
        """
        Return history.jsonl events with timestamps after self.prev_timestamp.

        Returns:
            List of history event dicts newer than the current watermark.
        """
        filtered = []
        try:
            history = FileIO.read_jsonl_file(self.history_file)
            print(f"{len(history)} history events read from {self.history_file}")
            for event in history:
                print(json.dumps(event, indent=2))
                event_timestamp = int(event["timestamp"])
                if event_timestamp > self.prev_timestamp:
                    filtered.append(event)
        except Exception as e:
            print(traceback.format_exc())
        return filtered

    def process_history_event(self, history_event: dict) -> list[dict]:
        """
        Load session JSONL events for a single history entry.

        Resolves the project path to a ~/.claude/projects/ directory and reads
        session files matching the history event's sessionId.

        Args:
            history_event: One record from history.jsonl (project, sessionId, timestamp).

        Returns:
            Project activity list (currently always empty; events append to self.telemetry_events).
        """
        project_activity = []
        try:
            history_epoch = int(history_event["timestamp"])
            execution_path = history_event["project"]
            session_id = history_event["sessionId"]
            claude_proj_dir = self.execution_path_as_claude_project_path(execution_path)
            self.project_session_events(claude_proj_dir, session_id, history_epoch)
        except Exception as e:
            print(traceback.format_exc())
        return project_activity

    def execution_path_as_claude_project_path(self, execution_path: str) -> str:
        """
        Map a workspace path to its ~/.claude/projects/ directory.

        Replaces path separators with hyphens to match Claude Code's project
        directory naming.

        Example:
            /Users/elsa/github/claude-code-telemetry
            -> ~/.claude/projects/-Users-elsa-github-claude-code-telemetry

        Args:
            execution_path: Absolute filesystem path of the Claude Code project.

        Returns:
            Expanded path to the matching projects subdirectory.
        """
        pname = execution_path.replace("/", "-")
        print(f"{execution_path} -> {pname} -> {os.path.expanduser(f'~/.claude/projects/{pname}')}")
        return os.path.expanduser(f"~/.claude/projects/{pname}")

    def timestamp_str_to_epoch(self, timestamp_str: str) -> int:
        """
        Convert an ISO-8601 timestamp string to epoch milliseconds.

        Args:
            timestamp_str: Value such as '2026-06-17T15:29:23.377Z'.

        Returns:
            Epoch milliseconds, or 0 if conversion fails.
        """
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except:
            print(traceback.format_exc())
            return 0

    def project_session_events(
        self, claude_proj_dir: str, session_id: str, history_epoch: int
    ) -> None:
        """
        Append session JSONL events at or after history_epoch to telemetry_events.

        Scans claude_proj_dir for <session_id>*.jsonl files and enriches model
        events with epoch, model name, and _event_source metadata.

        Args:
            claude_proj_dir: Path under ~/.claude/projects/ for the workspace.
            session_id: Session identifier from the history entry.
            history_epoch: Minimum event timestamp (ms) to include.
        """
        try:
            if os.path.isdir(claude_proj_dir):
                for session_file in os.listdir(claude_proj_dir):
                    if session_file.startswith(session_id):
                        if session_file.endswith(".jsonl"):
                            fq_session_file = os.path.join(claude_proj_dir, session_file)
                            events = FileIO.read_jsonl_file(fq_session_file)
                            print(
                                f"ClaudeUtil#project_session_events - fq_session_file: {fq_session_file} - {len(events)} events"
                            )
                            for event in events:
                                if "message" in event.keys():
                                    msg = event["message"]
                                    if "model" in msg.keys():
                                        if "timestamp" in event.keys():
                                            event_epoch = self.timestamp_str_to_epoch(
                                                event["timestamp"]
                                            )
                                            if event_epoch >= history_epoch:
                                                event["epoch"] = event_epoch
                                                event["model"] = msg["model"]
                                                event_source = dict()
                                                event_source["project"] = claude_proj_dir
                                                event_source["session"] = session_id
                                                event_source["user"] = self.user
                                                event["_event_source"] = event_source
                                                print(json.dumps(event, indent=2))
                                self.telemetry_events.append(event)
                        print(f"ClaudeUtil#project_session_events - session_file: {session_file}")
        except Exception as e:
            print(traceback.format_exc())

    def filter_captured_telemetry(self) -> None:
        """
        Keep only events with model usage and attach parent event chains.

        Replaces self.telemetry_events with the filtered list and updates
        self.data["telemetry_events"].
        """
        events_by_uuid = dict()
        for event in self.telemetry_events:
            if "uuid" in event.keys():
                events_by_uuid[event["uuid"]] = event

        filtered = []
        for event in self.telemetry_events:
            if self.event_has_model_usage(event):
                parent_events = []
                self.traverse_parent_events(events_by_uuid, event, parent_events, set[str]())
                event["parent_events"] = parent_events
                filtered.append(event)
        self.telemetry_events = filtered
        self.data["telemetry_events"] = self.telemetry_events

    def traverse_parent_events(
        self,
        events_by_uuid: dict,
        event: dict,
        parent_events: list[dict],
        visited: set[str] | None = None,
    ) -> list[dict]:
        """
        Walk parentUuid links and collect ancestor events with model usage.

        Args:
            events_by_uuid: All captured events keyed by uuid.
            event: Starting event whose parent chain should be traversed.
            parent_events: Output list; matching parents are appended in place.
            visited: Uuids already visited (guards against cycles).

        Returns:
            The parent_events list (same object passed in).
        """
        try:
            if visited is None:
                visited = set()
            parent_uuid = event.get("parentUuid")
            if parent_uuid and (parent_uuid not in visited) and (parent_uuid in events_by_uuid):
                visited.add(parent_uuid)
                parent_event = events_by_uuid[parent_uuid]
                if self.event_has_model_usage(parent_event):
                    parent_events.append(parent_event)
                    self.traverse_parent_events(
                        events_by_uuid, parent_event, parent_events, visited
                    )
        except Exception as e:
            print(traceback.format_exc())

    def event_has_model_usage(self, event: dict) -> bool:
        """
        Return True if the event contains a message with a model field.

        Args:
            event: A telemetry or session event dict.

        Returns:
            True when event["message"]["model"] is present.
        """
        if "message" in event.keys():
            msg = event["message"]
            if "model" in msg.keys():
                return True
        return False

    # IO methods below

    def read_last_history_timestamp(self) -> int:
        """
        Read the watermark timestamp from ~/.claudex/history_timestamp.txt.

        Returns:
            Last processed epoch milliseconds, or 0 if the file is missing.
        """
        try:
            with open(file=self.last_history_file, encoding="utf-8", mode="rt") as file:
                return int(file.read().strip())
        except Exception as e:
            print("Exception in ClaudeUtil#read_last_history_timestamp, returning 0")
            return 0

    def write_last_history_timestamp(self, timestamp: int) -> bool:
        """
        Persist the watermark timestamp to ~/.claudex/history_timestamp.txt.

        Args:
            timestamp: Epoch milliseconds to record as the last processed time.

        Returns:
            True on success, False on error.
        """
        try:
            ts = int(time.time())
            if isinstance(timestamp, int):
                ts = timestamp
            with open(file=self.last_history_file, encoding="utf-8", mode="wt") as file:
                file.write(str(ts))
            print(
                f"ClaudeUtil#write_last_history_timestamp - {timestamp} -> {self.last_history_file}"
            )
            return True
        except Exception as e:
            print(traceback.format_exc())
            return False
