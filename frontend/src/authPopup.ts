import { PublicClientApplication } from "@azure/msal-browser";
import { app as teamsApp, authentication as teamsAuthentication } from "@microsoft/teams-js";
import { loginRequest, msalConfig, popupRedirectUri } from "./authConfig";
import { writeAuthPopupResult, type AuthPopupResult } from "./authPopupBridge";
import "./authPopup.css";

const msalInstance = new PublicClientApplication(msalConfig);
const params = new URLSearchParams(window.location.search);
const AUTH_POPUP_NONCE_KEY = "sentinel-auth-popup-nonce";
const AUTH_POPUP_TEAMS_MODE_KEY = "sentinel-auth-popup-teams-mode";
const nonce = params.get("nonce") ?? sessionStorage.getItem(AUTH_POPUP_NONCE_KEY) ?? "";
const isTeamsAuthPopup = params.get("teamsAuth") === "1"
  || sessionStorage.getItem(AUTH_POPUP_TEAMS_MODE_KEY) === "1";

function publishAuthResult(message: Pick<AuthPopupResult, "type" | "homeAccountId" | "error">) {
  const result: AuthPopupResult = {
    source: "sentinel-auth-popup",
    nonce,
    createdAt: Date.now(),
    ...message,
  };

  writeAuthPopupResult(result);
  window.opener?.postMessage(result, window.location.origin);
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error || "Microsoft sign-in failed");
}

async function notifyTeamsAuthSuccess(result: AuthPopupResult): Promise<boolean> {
  if (!isTeamsAuthPopup) return false;

  try {
    await teamsApp.initialize();
    teamsAuthentication.notifySuccess(JSON.stringify(result));
    return true;
  } catch {
    return false;
  }
}

async function notifyTeamsAuthFailure(error: string): Promise<boolean> {
  if (!isTeamsAuthPopup) return false;

  try {
    await teamsApp.initialize();
    teamsAuthentication.notifyFailure(error);
    return true;
  } catch {
    return false;
  }
}

async function completePopupSignIn() {
  await msalInstance.initialize();

  const shouldStart = params.get("start") === "1";
  const prompt = params.get("prompt") || undefined;

  try {
    const result = await msalInstance.handleRedirectPromise();
    if (result?.account) {
      msalInstance.setActiveAccount(result.account);
      const popupResult: AuthPopupResult = {
        source: "sentinel-auth-popup",
        nonce,
        createdAt: Date.now(),
        type: "success",
        homeAccountId: result.account.homeAccountId,
      };
      writeAuthPopupResult(popupResult);
      if (await notifyTeamsAuthSuccess(popupResult)) return;
      publishAuthResult(popupResult);
      window.close();
      return;
    }

    if (shouldStart) {
      sessionStorage.setItem(AUTH_POPUP_NONCE_KEY, nonce);
      sessionStorage.setItem(AUTH_POPUP_TEAMS_MODE_KEY, isTeamsAuthPopup ? "1" : "0");
      await msalInstance.loginRedirect({
        scopes: loginRequest.scopes,
        redirectUri: popupRedirectUri,
        prompt: prompt === "select_account" ? "select_account" : undefined,
      });
      return;
    }

    const error = "Microsoft sign-in returned without an account.";
    if (await notifyTeamsAuthFailure(error)) return;
    publishAuthResult({
      type: "error",
      error,
    });
  } catch (error) {
    const errorMessage = getErrorMessage(error);
    if (await notifyTeamsAuthFailure(errorMessage)) return;
    publishAuthResult({
      type: "error",
      error: errorMessage,
    });
  }
}

void completePopupSignIn();