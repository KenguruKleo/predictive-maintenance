"""
Service Bus publisher — alert-queue.

Auth priority:
  1. SERVICEBUS_CONNECTION_STRING env var  (local dev)
  2. DefaultAzureCredential (Azure Functions Managed Identity)
"""

import json
import os

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage

SERVICEBUS_NAMESPACE = os.getenv(
    "SERVICEBUS_NAMESPACE",
    "sb-sentinel-intel-dev-erzrpo.servicebus.windows.net",
)
QUEUE_NAME = "alert-queue"


def publish_alert(payload: dict) -> None:
    """Publish alert payload to Service Bus alert-queue."""
    conn_str = os.getenv("SERVICEBUS_CONNECTION_STRING")

    if conn_str:
        sb_client = ServiceBusClient.from_connection_string(conn_str)
    else:
        sb_client = ServiceBusClient(
            fully_qualified_namespace=SERVICEBUS_NAMESPACE,
            credential=DefaultAzureCredential(),
        )

    message_body = json.dumps(payload, default=str)

    with sb_client:
        with sb_client.get_queue_sender(QUEUE_NAME) as sender:
            msg = ServiceBusMessage(
                body=message_body,
                content_type="application/json",
                subject=f"alert:{payload.get('incident_id', 'unknown')}",
                message_id=payload.get("incident_id"),
            )
            sender.send_messages(msg)
