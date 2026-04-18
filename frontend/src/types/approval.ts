export type DecisionAction = "approved" | "rejected" | "more_info";

export interface DecisionPayload {
  action: DecisionAction;
  user_id?: string;
  role?: "operator" | "qa-manager" | string;
  reason?: string;
  question?: string;
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
