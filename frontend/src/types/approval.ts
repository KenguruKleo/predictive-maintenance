export type DecisionAction = "approve" | "reject" | "more_info";

export interface DecisionPayload {
  action: DecisionAction;
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
