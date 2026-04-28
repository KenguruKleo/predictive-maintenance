export const AUTH_POPUP_RESULT_KEY = "sentinel-auth-popup-result";

export interface AuthPopupResult {
  source: "sentinel-auth-popup";
  nonce: string;
  type: "success" | "error";
  homeAccountId?: string;
  error?: string;
  createdAt: number;
}

export function parseAuthPopupResult(value: string | null, nonce: string): AuthPopupResult | null {
  if (!value) return null;

  try {
    const result = JSON.parse(value) as Partial<AuthPopupResult>;
    if (result.source !== "sentinel-auth-popup") return null;
    if (result.nonce !== nonce) return null;
    if (result.type !== "success" && result.type !== "error") return null;
    if (typeof result.createdAt !== "number") return null;
    return result as AuthPopupResult;
  } catch {
    return null;
  }
}

export function writeAuthPopupResult(result: AuthPopupResult) {
  localStorage.setItem(AUTH_POPUP_RESULT_KEY, JSON.stringify(result));
}