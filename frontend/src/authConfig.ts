/**
 * MSAL configuration for Sentinel Intelligence SPA (T-032 / T-035)
 *
 * SPA client:  1bdb80fb-950c-45b8-be9c-8f8a7fa26ca9  (sentinel-intelligence-spa)
 * API client:  38843d08-f211-4445-bcef-a07d383f2ee6  (sentinel-intelligence-api)
 * Tenant:      baf5b083-4c53-493a-8af7-a6ae9812014c
 */

import type { Configuration, PopupRequest, RedirectRequest } from "@azure/msal-browser";

// These env vars are injected at build time via Vite (VITE_* prefix)
const TENANT_ID =
  import.meta.env.VITE_ENTRA_TENANT_ID ?? "baf5b083-4c53-493a-8af7-a6ae9812014c";
const SPA_CLIENT_ID =
  import.meta.env.VITE_ENTRA_SPA_CLIENT_ID ?? "1bdb80fb-950c-45b8-be9c-8f8a7fa26ca9";
const API_CLIENT_ID =
  import.meta.env.VITE_ENTRA_API_CLIENT_ID ?? "38843d08-f211-4445-bcef-a07d383f2ee6";

export const msalConfig: Configuration = {
  auth: {
    clientId: SPA_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${TENANT_ID}`,
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: "sessionStorage",
  },
};

/** Scopes for the initial login — only OIDC scopes, no API scope.
 *  Requesting an API scope here causes 400 if the API app has no
 *  delegated (oauth2PermissionScopes) configured in Entra ID. */
export const loginRequest: RedirectRequest = {
  scopes: ["openid", "profile", "email"],
};

/** Scopes acquired silently when calling the backend API.
 *  Acquired separately after login via acquireTokenSilent. */
export const apiRequest: PopupRequest = {
  scopes: [`api://${API_CLIENT_ID}/.default`],
};

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api";
