# Emit Claude Code telemetry as OpenTelemetry spans to Azure App Insights or a local collector.
# Reads JSON payloads produced by ClaudeTelemetryUtil and exports each model-usage event
# as a span with LLM attributes (model name, token usage, session metadata).
# Chris Joakim, 2026

import json
import logging
import os
import time
import traceback
from datetime import datetime, timezone

from azure.monitor.opentelemetry import configure_azure_monitor

from opentelemetry import metrics
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

LOCALHOST_OTLP_GRPC_ENDPOINT = (
    "localhost:4317"  # gRPC exporter requires bare host:port, with no scheme
)


class OtelEmitter:
    """Export Claude telemetry JSON to OpenTelemetry backends."""

    def __init__(self):
        """Initialize an OtelEmitter instance."""

    def emit_to_azure_app_insights(self, telemetry_data: dict) -> int:
        """
        Send telemetry events to Azure Application Insights via OpenTelemetry.

        Configures the Azure Monitor exporter using APPLICATIONINSIGHTS_CONNECTION_STRING.
        Each event is logged as a compact JSON warning on the AppInsightsLogger, using the
        same attribute keys as emit_to_localhost_collector.

        Args:
            telemetry_data: Telemetry JSON dict with a telemetry_events list
                (as written by ClaudeTelemetryUtil).

        Returns:
            Number of events processed, or -1 on error.
        """
        try:
            print("OtelEmitter#emit_to_azure_app_insights")
            # This automatically reads the APPLICATIONINSIGHTS_CONNECTION_STRING environment variable
            configure_azure_monitor()

            app_insights_logger = logging.getLogger("AppInsightsLogger")
            app_insights_logger.setLevel(logging.WARNING)

            events = telemetry_data.get("telemetry_events", [])
            for event in events:
                payload = self._event_payload(event)
                print(json.dumps(payload, indent=2))
                app_insights_logger.warning(json.dumps(payload))
                time.sleep(0.1)
            return len(events)
        except Exception as e:
            print(f"Exception in OtelEmitter#emit_to_azure_app_insights: {e}")
            print(traceback.format_exc())
            return -1

    def emit_to_localhost_collector(self, telemetry_data: dict) -> int:
        """
        Emit telemetry events as OTLP gRPC spans to a local collector.

        Creates one span per event with claude/<model> name and attributes for
        uuid, session, cwd, git branch, request id, version, and token usage.
        Spans are exported to localhost:4317 (standard OTEL collector gRPC port).

        Args:
            telemetry_data: Telemetry JSON dict with a telemetry_events list.

        Returns:
            Number of spans emitted, or -1 on error.
        """
        try:
            print("OtelEmitter#emit_to_localhost_collector")

            resource = Resource(attributes={SERVICE_NAME: "claude-code-telemetry"})
            exporter = OTLPSpanExporter(endpoint=LOCALHOST_OTLP_GRPC_ENDPOINT, insecure=True)
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            tracer = trace.get_tracer("claude-code-telemetry")
            batch_name = "batch1"

            events = telemetry_data.get("telemetry_events", [])
            count = 0
            for event in events:
                try:
                    print(f"Emitting event {json.dumps(event, indent=2)}")
                    start_ns = self._iso_to_ns(event.get("timestamp", ""))
                    end_ns = start_ns + 1_000_000  # 1ms placeholder duration
                    msg = event.get("message", {})
                    model = msg.get("model", "unknown")

                    span = tracer.start_span(f"claude/{model}", start_time=start_ns)
                    for key, value in self._event_payload(event, batch_name).items():
                        span.set_attribute(key, value)
                    print(f"Span: {span.to_json()}")  # <class 'opentelemetry.sdk.trace._Span'>

                    span.end(end_time=end_ns)
                    count += 1
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Error emitting event {event.get('uuid', '?')}: {e}")

            provider.shutdown()
            print(
                f"OtelEmitter#emit_to_localhost_collector - emitted {count} events to {LOCALHOST_OTLP_GRPC_ENDPOINT}"
            )
            print("Visit http://localhost:16686/ with your web browser to see the traces")
            return count
        except Exception as e:
            print(f"Exception in OtelEmitter#emit_to_localhost_collector: {e}")
            print(traceback.format_exc())
            return -1

    def _event_payload(self, event: dict, batch_name: str = "batch1") -> dict:
        """
        Build a compact attribute dict shared by Azure and localhost emitters.

        Args:
            event: A single telemetry event from ClaudeTelemetryUtil.
            batch_name: Batch label attached to each event.

        Returns:
            Dict of attribute keys to values (mirrors OTLP span attributes).
        """
        msg = event.get("message", {})
        model = msg.get("model", "unknown")
        payload = {
            "event.uuid": event.get("uuid", ""),
            "event.session_id": event.get("sessionId", ""),
            "event.type": event.get("type", ""),
            "event.cwd": event.get("cwd", ""),
            "event.git_branch": event.get("gitBranch", ""),
            "event.request_id": event.get("requestId", ""),
            "event.version": event.get("version", ""),
            "llm.model": model,
            "batch.name": batch_name,
        }
        usage = msg.get("usage", {})
        if usage:
            payload["llm.usage.input_tokens"] = usage.get("input_tokens", 0)
            payload["llm.usage.output_tokens"] = usage.get("output_tokens", 0)
            payload["llm.usage.cache_creation_input_tokens"] = usage.get(
                "cache_creation_input_tokens", 0
            )
            payload["llm.usage.cache_read_input_tokens"] = usage.get("cache_read_input_tokens", 0)
        return payload

    def _iso_to_ns(self, ts_str: str) -> int:
        """
        Convert an ISO-8601 timestamp string to nanoseconds since the Unix epoch.

        Args:
            ts_str: Value such as '2026-06-17T15:29:23.377Z'.

        Returns:
            Nanoseconds since epoch, or the current time if conversion fails.
        """
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1_000_000_000)
        except Exception:
            return int(time.time() * 1_000_000_000)
