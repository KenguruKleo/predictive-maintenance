import axios, { AxiosHeaders } from "axios";
import { PublicClientApplication } from "@azure/msal-browser";
import type { InternalAxiosRequestConfig } from "axios";
import { API_BASE_URL, apiRequest } from "../authConfig";
import { getE2ERequestHeaders, IS_E2E_AUTH } from "../authRuntime";
import { clearTeamsAuthToken, getTeamsAuthState, setTeamsAuthToken } from "../teamsAuth";
import { getTeamsSsoToken, isLikelyTeamsHost } from "../teamsRuntime";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

let msalInstance: PublicClientApplication | null = null;

function getMsalErrorCode(error: unknown): string {
  if (!error || typeof error !== "object") return "";
  const errorCode = (error as { errorCode?: unknown }).errorCode;
  return typeof errorCode === "string" ? errorCode : "";
}

function requiresInteractiveTokenAcquisition(error: unknown): boolean {
  const errorCode = getMsalErrorCode(error);
  return errorCode === "consent_required"
    || errorCode === "interaction_required"
    || errorCode === "login_required";
}

function setHeader(
  config: InternalAxiosRequestConfig,
  name: string,
  value: string,
) {
  const headers = AxiosHeaders.from(config.headers ?? {});
  headers.set(name, value);
  config.headers = headers;
}

export function getApiErrorStatus(error: unknown): number | undefined {
  return axios.isAxiosError(error) ? error.response?.status : undefined;
}

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    if (data && typeof data === "object" && "error" in data) {
      const message = (data as { error?: unknown }).error;
      if (typeof message === "string" && message.trim()) return message;
    }
    if (typeof data === "string" && data.trim()) return data;
  }

  if (error instanceof Error && error.message.trim()) return error.message;
  return String(error || "Request failed");
}

export function isUnauthorizedApiError(error: unknown): boolean {
  return getApiErrorStatus(error) === 401;
}

export function isForbiddenApiError(error: unknown): boolean {
  return getApiErrorStatus(error) === 403;
}

function recoverFromUnauthorizedApiError(error: unknown) {
  if (IS_E2E_AUTH || !isUnauthorizedApiError(error)) {
    return Promise.reject(error);
  }

  if (getTeamsAuthState().isAuthenticated) {
    clearTeamsAuthToken();
  }

  if (isLikelyTeamsHost()) {
    clearTeamsAuthToken();
  }

  return Promise.reject(error);
}

export function setMsalInstance(instance: PublicClientApplication) {
  msalInstance = instance;
}

client.interceptors.request.use(async (config) => {
  if (IS_E2E_AUTH) {
    const headers = getE2ERequestHeaders();
    setHeader(config, "X-Mock-Role", headers["X-Mock-Role"]);
    setHeader(config, "X-Mock-User", headers["X-Mock-User"]);
    setHeader(config, "X-Mock-User-Id", headers["X-Mock-User"]);
    return config;
  }

  if (getTeamsAuthState().isAuthenticated) {
    try {
      const token = await getTeamsSsoToken();
      setTeamsAuthToken(token);
      setHeader(config, "Authorization", `Bearer ${token}`);
      return config;
    } catch {
      const token = getTeamsAuthState().accessToken;
      if (token) {
        setHeader(config, "Authorization", `Bearer ${token}`);
        return config;
      }
    }
  }

  if (!msalInstance) return config;
  const account = msalInstance.getActiveAccount();
  if (!account) return config;
  try {
    const result = await msalInstance.acquireTokenSilent({
      ...apiRequest,
      account,
    });
    setHeader(config, "Authorization", `Bearer ${result.accessToken}`);
  } catch (error) {
    if (requiresInteractiveTokenAcquisition(error)) {
      const message = isLikelyTeamsHost()
        ? "Interactive Microsoft sign-in is disabled inside Teams. Use Teams SSO or open Sentinel in the browser."
        : "Sentinel needs permission to call the API. Sign out and sign in again, or ask an admin to grant API consent.";
      return Promise.reject(new Error(message));
    }

    return Promise.reject(error);
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  recoverFromUnauthorizedApiError,
);

export default client;
