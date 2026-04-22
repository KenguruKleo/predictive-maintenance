export type DecisionAction = "approved" | "rejected" | "more_info";

export interface WorkOrderDraft {
  title?: string;
  description?: string;
  priority?: string;
  work_type?: string;
}

export interface AuditEntryDraft {
  deviation_type?: string;
  gmp_clause?: string;
  description?: string;
  root_cause?: string;
}

export interface DecisionPayload {
  action: DecisionAction;
  user_id?: string;
  role?: "operator" | "qa-manager" | string;
  reason?: string;
  question?: string;
  agent_recommendation?: "APPROVE" | "REJECT";
  work_order_draft?: WorkOrderDraft;
  audit_entry_draft?: AuditEntryDraft;
}

export interface ChatMessage {
  id: string;
  incident_id: string;
  timestamp: string;
  actor: string;
  actor_type: "human" | "agent";
  content: string;
  updated_fields?: string[];
}
