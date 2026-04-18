export type Severity = "critical" | "major" | "moderate" | "minor";

export type IncidentStatus =
  | "open"
  | "ingested"
  | "analyzing"
  | "pending_approval"
  | "escalated"
  | "approved"
  | "rejected"
  | "closed";

export type RiskLevel = "HIGH" | "MEDIUM" | "LOW" | "LOW_CONFIDENCE";

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
  nor_min: number;
  nor_max: number;
  par_min: number;
  par_max: number;
  duration_seconds: number;
}

export interface EvidenceCitation {
  type: "sop" | "historical" | "gmp" | "bpr";
  reference: string;
  section?: string;
  relevance: string;
}

export interface CapaStep {
  step: number;
  description: string;
  priority: string;
}

export interface AiAnalysis {
  risk_level: RiskLevel;
  confidence: number;
  deviation_classification: string;
  root_cause_hypothesis: string;
  capa_steps: CapaStep[];
  evidence_citations: EvidenceCitation[];
  batch_disposition?: BatchDispositionStatus;
  disposition_conditions?: string[];
}

export interface DocumentDraft {
  type: "work_order" | "audit_entry";
  title: string;
  content: Record<string, unknown>;
}

export interface WorkflowState {
  current_step: string;
  steps_completed: number;
  total_steps: number;
}

export interface Incident {
  id: string;
  incident_number?: string;
  title?: string;
  equipment_id: string;
  batch_id?: string;
  product?: string;
  production_stage?: string;
  severity: Severity;
  status: IncidentStatus;
  assigned_to?: string;
  reported_at?: string;
  created_at?: string;
  updated_at?: string;
  parameter_excursion?: ParameterExcursion;
  ai_analysis?: AiAnalysis;
  document_drafts?: DocumentDraft[];
  workflow_state?: WorkflowState;
}

export interface IncidentEvent {
  id: string;
  incident_id: string;
  timestamp: string;
  actor: string;
  actor_type: "system" | "agent" | "human";
  action: string;
  details: string;
  updated_fields?: string[];
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
  "pending_approval",
  "escalated",
  "approved",
] as const satisfies IncidentStatus[];
