export type Severity = "critical" | "major" | "moderate" | "minor";

export type IncidentStatus =
  | "open"
  | "ingested"
  | "analyzing"
  | "pending_approval"
  | "escalated"
  | "awaiting_agents"
  | "approved"
  | "in_progress"
  | "executed"
  | "completed"
  | "rejected"
  | "closed";

export type RiskLevel =
  | "CRITICAL"
  | "HIGH"
  | "MEDIUM"
  | "LOW"
  | "LOW_CONFIDENCE"
  | "critical"
  | "high"
  | "medium"
  | "low"
  | (string & {});

export type BatchDispositionStatus =
  | "in_production"
  | "hold"
  | "conditional_release"
  | "released"
  | "rejected"
  | "pending"
  | "quarantine"
  | "under_review"
  | (string & {});

export interface ParameterExcursion {
  parameter: string;
  measured_value: number;
  unit: string;
  nor_min?: number;
  nor_max?: number;
  par_min?: number;
  par_max?: number;
  lower_limit?: number;
  upper_limit?: number;
  duration_seconds: number;
}

export interface EvidenceCitation {
  type?: "sop" | "historical" | "gmp" | "bpr" | "manual" | "incident" | (string & {});
  source?: string;
  reference?: string;
  document_id?: string;
  document_title?: string;
  section?: string;
  relevant_section?: string;
  relevance?: string;
  text_excerpt?: string;
  source_blob?: string;
  container?: string;
  index_name?: string;
  chunk_index?: number;
  score?: number;
  url?: string;
  resolution_status?: "resolved" | "unresolved";
  unresolved_reason?: string;
}

export interface CapaStep {
  step: number;
  description: string;
  priority: string;
}

export interface AiAnalysis {
  risk_level: RiskLevel;
  confidence: number;
  deviation_classification?: string;
  classification?: string;
  root_cause_hypothesis?: string;
  root_cause?: string;
  analysis?: string;
  recommendation?: string;
  capa_suggestion?: string;
  recommendations?: {
    action: string;
    priority?: string;
    owner?: string;
    deadline_days?: number;
  }[];
  capa_steps?: CapaStep[];
  evidence_citations: EvidenceCitation[];
  regulatory_reference?: string;
  regulatory_refs?: EvidenceCitation[] | string[];
  sop_refs?: EvidenceCitation[] | string[];
  batch_disposition?: BatchDispositionStatus;
  disposition_conditions?: string[];
  work_order_draft?: Record<string, unknown>;
  audit_entry_draft?: Record<string, unknown>;
  agent_recommendation?: "APPROVE" | "REJECT";
}

export interface DocumentDraft {
  type: "work_order" | "audit_entry";
  title: string;
  content: Record<string, unknown>;
}

export interface WorkflowState {
  current_step: string;
  steps_completed?: number;
  total_steps?: number;
  assigned_to?: string;
  target_role?: string;
  approval_task_id?: string;
  escalation_deadline?: string;
}

export interface LastDecision {
  action: "approved" | "rejected" | "more_info" | string;
  user_id?: string;
  role?: string;
  reason?: string;
  question?: string;
  agent_recommendation?: "APPROVE" | "REJECT";
  operator_agrees_with_agent?: boolean | null;
}

export interface Incident {
  id: string;
  incident_number?: string;
  title?: string;
  equipment_id: string;
  equipment_name?: string;
  equipment_type?: string;
  equipment_criticality?: string;
  location?: string | Record<string, string>;
  deviation_type?: string;
  batch_id?: string;
  product?: string;
  production_stage?: string;
  severity: Severity;
  status: IncidentStatus;
  assigned_to?: string;
  reported_at?: string;
  created_at?: string;
  updated_at?: string;
  parameter?: string;
  measured_value?: number;
  lower_limit?: number;
  upper_limit?: number;
  unit?: string;
  duration_seconds?: number;
  parameter_excursion?: ParameterExcursion;
  ai_analysis?: AiAnalysis;
  document_drafts?: DocumentDraft[];
  workflow_state?: WorkflowState;
  lastDecision?: LastDecision;
  finalDecision?: LastDecision;
  rejectionReason?: string;
  agentRecommendation?: "APPROVE" | "REJECT";
  operatorAgreesWithAgent?: boolean | null;
  operatorWorkOrderDraft?: Record<string, unknown>;
  operatorAuditEntryDraft?: Record<string, unknown>;
}

export interface IncidentEvent {
  id: string;
  incident_id: string;
  timestamp: string;
  actor: string;
  actor_type: "system" | "agent" | "human";
  action: string;
  category?: "status" | "transcript";
  details: string;
  round?: number | null;
  message_kind?: string;
  status?: string;
  updated_fields?: string[];
}

export type AgentTelemetryStatus = "started" | "completed" | "failed";

export type AgentTelemetryAgentName =
  | "orchestrator"
  | "research"
  | "document"
  | "execution"
  | "tool";

export interface IncidentTelemetryItem {
  id: string;
  timestamp: string;
  round: number;
  trace_kind: string;
  title: string;
  status: AgentTelemetryStatus;
  agent_name: AgentTelemetryAgentName | (string & {});
  source: "app_insights" | (string & {});
  content_type: "json" | "text" | (string & {});
  content: string;
  preview: string;
  metadata: Record<string, unknown>;
  chunk_count: number;
  content_length: number;
  run_id?: string | null;
  thread_id?: string | null;
  token_usage?: {
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    total_tokens?: number | null;
    model?: string | null;
  } | null;
}

export interface IncidentTelemetrySummary {
  total_items: number;
  started_items: number;
  completed_items: number;
  failed_items: number;
  rounds: number[];
  agent_names: string[];
  trace_kinds: string[];
  total_content_chars: number;
  total_duration_ms?: number | null;
  last_timestamp?: string | null;
  view_scope: string;
  total_prompt_tokens?: number | null;
  total_completion_tokens?: number | null;
  total_tokens?: number | null;
}

export interface IncidentTelemetryFilters {
  agent_name?: AgentTelemetryAgentName | "";
  status?: AgentTelemetryStatus | "";
  round?: number;
}

export interface IncidentTelemetryResponse {
  incident_id: string;
  summary: IncidentTelemetrySummary;
  items: IncidentTelemetryItem[];
  query: {
    agent_name?: string | null;
    status?: string | null;
    round?: number | null;
  };
  scope: {
    source: string;
    view: string;
    limitations: string[];
  };
}

export interface IncidentListResponse {
  items: Incident[];
  total: number;
  page: number;
  page_size: number;
}

export interface IncidentFilters {
  status?: IncidentStatus | IncidentStatus[];
  severity?: Severity;
  equipment_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

/** All statuses that represent an in-progress (non-terminal) incident. */
export const ACTIVE_INCIDENT_STATUSES = [
  "open",
  "ingested",
  "analyzing",
  "awaiting_agents",
  "pending_approval",
  "escalated",
  "approved",
  "in_progress",
] as const satisfies IncidentStatus[];
