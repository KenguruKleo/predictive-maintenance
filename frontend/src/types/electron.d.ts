export interface SentinelDesktopNotification {
  title: string;
  body: string;
  incidentId?: string;
}

export interface SentinelDesktopBridge {
  platform: string;
  setUnreadCount(count: number): void;
  notify(payload: SentinelDesktopNotification): void;
  onOpenIncident(callback: (incidentId: string) => void): () => void;
}

declare global {
  interface Window {
    sentinelDesktop?: SentinelDesktopBridge;
  }
}