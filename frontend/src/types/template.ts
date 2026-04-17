export interface Template {
  id: string;
  name: string;
  type: "work_order" | "audit_entry";
  version: string;
  description_template: string;
  default_priority?: string;
  assigned_team?: string;
  fields: string[];
  last_modified_by: string;
  last_modified_at: string;
}
