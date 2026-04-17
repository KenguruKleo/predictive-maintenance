"""
Azure Functions entry point — Predictive Maintenance / GMP Deviation Assistant.

Blueprints registered here:
  - triggers.http_ingest_alert     (T-023) POST /api/alerts
  - triggers.service_bus_trigger   (T-024) SB alert-queue → start orchestrator
  - triggers.http_decision         (T-024) POST /api/incidents/{id}/decision
  - orchestrators.incident_orchestrator  (T-024) Durable workflow
  - activities.enrich_context      (T-024) Cosmos DB context enrichment
  - activities.run_foundry_agents  (T-024) Foundry Orchestrator Agent
  - activities.notify_operator     (T-024) SignalR notification
  - activities.close_incident      (T-024) Set status=rejected
  - activities.run_execution_agent (T-024) CAPA execution (second half)
  - activities.finalize_audit      (T-024) Final audit record
"""

import azure.functions as func

from activities.close_incident import bp as close_incident_bp
from activities.enrich_context import bp as enrich_context_bp
from activities.finalize_audit import bp as finalize_audit_bp
from activities.notify_operator import bp as notify_operator_bp
from activities.run_execution_agent import bp as run_execution_agent_bp
from activities.run_foundry_agents import bp as run_foundry_agents_bp
from orchestrators.incident_orchestrator import bp as orchestrator_bp
from triggers.http_decision import bp as decision_bp
from triggers.http_ingest_alert import bp as ingest_bp
from triggers.service_bus_trigger import bp as sb_trigger_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ── HTTP triggers ─────────────────────────────────────────────────────────
app.register_functions(ingest_bp)
app.register_functions(decision_bp)

# ── Service Bus trigger ───────────────────────────────────────────────────
app.register_functions(sb_trigger_bp)

# ── Durable orchestrator ──────────────────────────────────────────────────
app.register_functions(orchestrator_bp)

# ── Durable activities ────────────────────────────────────────────────────
app.register_functions(enrich_context_bp)
app.register_functions(run_foundry_agents_bp)
app.register_functions(notify_operator_bp)
app.register_functions(close_incident_bp)
app.register_functions(run_execution_agent_bp)
app.register_functions(finalize_audit_bp)

