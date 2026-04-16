"""
Azure Functions entry point — Predictive Maintenance / GMP Deviation Assistant.

Stub: registers the FunctionApp instance. Actual functions are added in
subsequent tasks (T-023 ingestion, T-031 HTTP API, T-029 approval webhook).
"""

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
