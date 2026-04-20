export type BrowserNotificationPermission = NotificationPermission | "unsupported";

export interface NotificationItem {
  id: string;
  incident_id: string;
  type: string;
  message: string;
  target_role: string;
  assigned_to: string;
  equipment_id: string;
  title: string;
  incident_status: string;
  confidence: number;
  risk_level: string;
  created_at: string;
  updated_at: string;
  is_read: boolean;
  read_at?: string | null;
  read_by?: string | null;
}

export interface NotificationsResponse {
  items: NotificationItem[];
  total: number;
  unread_count: number;
}

export interface NotificationSummary {
  unread_count: number;
  unread_incident_ids: string[];
  by_type: Record<string, number>;
  latest_unread_at?: string | null;
}

export interface MarkNotificationsReadResponse {
  incident_id: string;
  marked_read: number;
  notification_ids: string[];
}