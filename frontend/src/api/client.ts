import axios, { AxiosHeaders } from "axios";
import { PublicClientApplication } from "@azure/msal-browser";
import type { InternalAxiosRequestConfig } from "axios";
import { API_BASE_URL, apiRequest } from "../authConfig";
import { getE2ERequestHeaders, IS_E2E_AUTH } from "../authRuntime";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

let msalInstance: PublicClientApplication | null = null;

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

  if (!msalInstance) return config;
  const account = msalInstance.getActiveAccount();
  if (!account) return config;
  try {
    const result = await msalInstance.acquireTokenSilent({
      ...apiRequest,
      account,
    });
    setHeader(config, "Authorization", `Bearer ${result.accessToken}`);
  } catch {
    // Token acquisition failed — let request proceed without token
    // (backend will return 401, UI will handle)
  }
  return config;
});

export default client;
