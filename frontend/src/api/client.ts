import axios from "axios";
import { PublicClientApplication } from "@azure/msal-browser";
import { API_BASE_URL, apiRequest } from "../authConfig";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

let msalInstance: PublicClientApplication | null = null;

export function setMsalInstance(instance: PublicClientApplication) {
  msalInstance = instance;
}

client.interceptors.request.use(async (config) => {
  if (!msalInstance) return config;
  const account = msalInstance.getActiveAccount();
  if (!account) return config;
  try {
    const result = await msalInstance.acquireTokenSilent({
      ...apiRequest,
      account,
    });
    config.headers.Authorization = `Bearer ${result.accessToken}`;
  } catch {
    // Token acquisition failed — let request proceed without token
    // (backend will return 401, UI will handle)
  }
  return config;
});

export default client;
