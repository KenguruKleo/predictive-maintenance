import axios, { AxiosHeaders } from "axios";
import { PublicClientApplication } from "@azure/msal-browser";
import type { InternalAxiosRequestConfig } from "axios";
import { API_BASE_URL, apiRequest } from "../authConfig";
import { getE2ERequestHeaders, IS_E2E_AUTH } from "../authRuntime";
import { getTeamsAuthState, setTeamsAuthToken } from "../teamsAuth";
import { getTeamsSsoToken, isLikelyTeamsHost } from "../teamsRuntime";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

let msalInstance: PublicClientApplication | null = null;
let tokenRedirectInFlight = false;

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
    if (requiresInteractiveTokenAcquisition(error) && !tokenRedirectInFlight) {
      if (isLikelyTeamsHost()) {
        return Promise.reject(new Error("Interactive Microsoft sign-in is disabled inside Teams. Use Teams SSO or open Sentinel in the browser."));
      }
      tokenRedirectInFlight = true;
      void msalInstance.acquireTokenRedirect({
        ...apiRequest,
        account,
        redirectStartPage: window.location.href,
        ...(getMsalErrorCode(error) === "consent_required" ? { prompt: "consent" as const } : {}),
      }).finally(() => {
        tokenRedirectInFlight = false;
      });
    }

    return Promise.reject(error);
  }
  return config;
});

export default client;
