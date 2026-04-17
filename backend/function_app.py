"""
Azure Functions entry point — Predictive Maintenance / GMP Deviation Assistant.

Blueprints registered here:
  - triggers.http_ingest_alert  (T-023) POST /api/alerts
  # T-031 backend API endpoints added next
  # T-029 human approval webhook added next
"""

import azure.functions as func

from triggers.http_ingest_alert import bp as ingest_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

app.register_functions(ingest_bp)
