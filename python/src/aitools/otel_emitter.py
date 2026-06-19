import json
import logging
import time
import traceback

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import metrics

from src.io.fileio import FileIO


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

    def emit_to_localhost_collector(self, telemetry_data: list[dict]) -> int:
        try:
            print("OtelEmitter#emit_to_localhost_collector")
            for event in telemetry_data["telemetry_events"]:
                print(json.dumps(event, indent=2))
            return len(telemetry_data)
        except Exception as e:
            print(f"Exception in OtelEmitter#emit_to_localhost_collector: {e}")
            print(traceback.format_exc())
            return -1
