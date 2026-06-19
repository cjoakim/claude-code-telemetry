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
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

LOCALHOST_OTLP_GRPC_ENDPOINT = "localhost:4317"


class OtelEmitter:
    def __init__(self):
        pass

    def emit_to_azure_app_insights(self, telemetry_data: list[dict]) -> int:
        try:
            print("OtelEmitter#emit_to_localhost_collector")
            # This automatically reads the APPLICATIONINSIGHTS_CONNECTION_STRING environment variable
            configure_azure_monitor()

            app_insights_logger = logging.getLogger("AppInsightsLogger")
            app_insights_logger.setLevel(logging.WARNING)

            for event in telemetry_data["telemetry_events"]:
                print(json.dumps(event, indent=2))
                app_insights_logger.warning(json.dumps(event))
                time.sleep(0.1)
            return len(telemetry_data)
        except Exception as e:
            print(f"Exception in OtelEmitter#emit_to_azure_app_insights: {e}")
            print(traceback.format_exc())
            return -1

    def emit_to_localhost_collector(self, telemetry_data: dict) -> int:
        try:
            print("OtelEmitter#emit_to_localhost_collector")

            resource = Resource(attributes={SERVICE_NAME: "claude-code-telemetry"})
            exporter = OTLPSpanExporter(endpoint=LOCALHOST_OTLP_GRPC_ENDPOINT, insecure=True)
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(BatchSpanProcessor(exporter))
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
                    span.set_attribute("event.uuid", event.get("uuid", ""))
                    span.set_attribute("event.session_id", event.get("sessionId", ""))
                    span.set_attribute("event.type", event.get("type", ""))
                    span.set_attribute("event.cwd", event.get("cwd", ""))
                    span.set_attribute("event.git_branch", event.get("gitBranch", ""))
                    span.set_attribute("event.request_id", event.get("requestId", ""))
                    span.set_attribute("event.version", event.get("version", ""))
                    span.set_attribute("llm.model", model)
                    span.set_attribute("batch.name", batch_name)

                    usage = msg.get("usage", {})
                    if usage:
                        span.set_attribute("llm.usage.input_tokens", usage.get("input_tokens", 0))
                        span.set_attribute("llm.usage.output_tokens", usage.get("output_tokens", 0))
                        span.set_attribute(
                            "llm.usage.cache_creation_input_tokens",
                            usage.get("cache_creation_input_tokens", 0),
                        )
                        span.set_attribute(
                            "llm.usage.cache_read_input_tokens",
                            usage.get("cache_read_input_tokens", 0),
                        )
                    print(f"Span: {span.to_json()}")  # <class 'opentelemetry.sdk.trace._Span'>

                    span.end(end_time=end_ns)
                    count += 1
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Error emitting event {event.get('uuid', '?')}: {e}")

            provider.shutdown()
            print(f"OtelEmitter#emit_to_localhost_collector - emitted {count} events")
            return count
        except Exception as e:
            print(f"Exception in OtelEmitter#emit_to_localhost_collector: {e}")
            print(traceback.format_exc())
            return -1

    def _iso_to_ns(self, ts_str: str) -> int:
        """Convert an ISO 8601 timestamp string to nanoseconds since Unix epoch."""
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1_000_000_000)
        except Exception:
            return int(time.time() * 1_000_000_000)
