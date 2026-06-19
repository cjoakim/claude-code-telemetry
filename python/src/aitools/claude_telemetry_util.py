import json
import os
import socket
import time
import traceback
from datetime import datetime, timezone
from typing import Any

from src.io.fileio import FileIO


class ClaudeTelemetryUtil:
    def __init__(self):
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

    def capture_usage(self, deep: bool = False) -> str | None:
        """
        Capture the recent Claude telemetry events since the last timestamp.
        Return the filename of the JSON file where self.data is written to.
        Return None if no data was captured.
        """
        try:
            self.prev_timestamp = self.read_last_history_timestamp()
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
            self.write_last_history_timestamp(0)  # TODO change 0 to self.last_timestamp

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
        return ""  # TODO implement

    def read_new_history_events(self) -> list[dict]:
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
        project_activity = []
        try:
            execution_path = history_event["project"]
            session_id = history_event["sessionId"]
            claude_proj_dir = self.execution_path_as_claude_project_path(execution_path)
            self.project_session_events(claude_proj_dir, session_id)
        except Exception as e:
            print(traceback.format_exc())
        return project_activity

    def execution_path_as_claude_project_path(self, execution_path: str) -> str:
        pname = execution_path.replace("/", "-")
        return os.path.expanduser(f"~/.claude/projects/{pname}")

    def timestamp_str_to_epoch(self, timestamp_str: str) -> int:
        """Given a timestamp string like '2026-06-17T15:29:23.377Z', return epoch milliseconds."""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except Exception as e:
            print(traceback.format_exc())
            return 0

    def project_session_events(self, claude_proj_dir: str, session_id: str) -> None:
        try:
            if os.path.isdir(claude_proj_dir):
                for session_file in os.listdir(claude_proj_dir):
                    if session_file.startswith(session_id):
                        fq_session_file = os.path.join(claude_proj_dir, session_file)
                        print(f"ClaudeUtil#project_session_events - {fq_session_file}")
                        # events = FileIO.read_jsonl_file(fq_session_file)
                        events = []
                        print(
                            f"ClaudeUtil#project_session_events - {fq_session_file} - {len(events)} events"
                        )
                        for event in events:
                            event["event_source"] = f"session_file_{session_id}"
                            self.telemetry_events.append(event)
        except Exception as e:
            print(traceback.format_exc())

    def filter_captured_telemetry(self) -> None:
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
        if "message" in event.keys():
            msg = event["message"]
            if "model" in msg.keys():
                return True
        return False

    # IO methods below

    def read_last_history_timestamp(self) -> int:
        try:
            with open(file=self.last_history_file, encoding="utf-8", mode="rt") as file:
                return int(file.read().strip())
        except Exception as e:
            print("Exception in ClaudeUtil#read_last_history_timestamp, returning 0")
            return 0

    def write_last_history_timestamp(self, timestamp: int) -> bool:
        try:
            ts = int(time.time())
            if isinstance(timestamp, int):
                ts = timestamp
            with open(file=self.last_history_file, encoding="utf-8", mode="wt") as file:
                file.write(str(ts))
            print(f"ClaudeUtil#write_last_history_timestamp - {timestamp}")
            return True
        except Exception as e:
            print(traceback.format_exc())
            return False
