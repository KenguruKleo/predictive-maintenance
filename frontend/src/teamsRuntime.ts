import { app, authentication } from "@microsoft/teams-js";

const TEAMS_INIT_TIMEOUT_MS = 1500;

type TeamsContext = Awaited<ReturnType<typeof app.getContext>>;

export interface TeamsRuntimeState {
  isTeams: boolean;
  context: TeamsContext | null;
  error: string | null;
}

let initializationPromise: Promise<TeamsRuntimeState> | null = null;

function timeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error(message)), timeoutMs);
    promise.then(
      (value) => {
        window.clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        window.clearTimeout(timer);
        reject(error);
      },
    );
  });
}

function isEmbeddedFrame(): boolean {
  try {
    return window.self !== window.top;
  } catch {
    return true;
  }
}

export function isLikelyTeamsHost(): boolean {
  if (typeof window === "undefined") return false;

  const params = new URLSearchParams(window.location.search);
  return isEmbeddedFrame()
    || params.has("hostClientType")
    || params.has("tenantId")
    || params.has("teamId")
    || params.has("channelId");
}

export function isLikelyTeamsWebHost(): boolean {
  if (typeof window === "undefined") return false;

  const params = new URLSearchParams(window.location.search);
  return params.get("hostClientType") === "web"
    || /^https:\/\/teams\.microsoft\.com\//i.test(document.referrer);
}

export async function initializeTeamsRuntime(): Promise<TeamsRuntimeState> {
  if (!isLikelyTeamsHost()) {
    return { isTeams: false, context: null, error: null };
  }

  initializationPromise ??= (async () => {
    try {
      await timeout(app.initialize(), TEAMS_INIT_TIMEOUT_MS, "Teams host did not respond");
      const context = await timeout(
        app.getContext(),
        TEAMS_INIT_TIMEOUT_MS,
        "Teams context did not respond",
      ).catch(() => null);
      return { isTeams: true, context, error: null };
    } catch (error) {
      return {
        isTeams: false,
        context: null,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  })();

  return initializationPromise;
}

export async function getTeamsSsoToken(): Promise<string> {
  const runtime = await initializeTeamsRuntime();
  if (!runtime.isTeams) {
    throw new Error(runtime.error ?? "This page is not running inside Microsoft Teams");
  }

  return authentication.getAuthToken();
}

export async function authenticateWithTeamsPopup(url: string): Promise<string> {
  const runtime = await initializeTeamsRuntime();
  if (!runtime.isTeams) {
    throw new Error(runtime.error ?? "This page is not running inside Microsoft Teams");
  }

  return authentication.authenticate({
    url,
    width: 600,
    height: 680,
  });
}

export async function isTeamsWebHost(): Promise<boolean> {
  if (isLikelyTeamsWebHost()) return true;

  const runtime = await initializeTeamsRuntime();
  return runtime.context?.app.host.clientType === "web";
}

export async function openAppInBrowser(): Promise<void> {
  const url = window.location.origin;
  const runtime = await initializeTeamsRuntime();

  if (runtime.isTeams) {
    await app.openLink(url);
    return;
  }

  window.open(url, "_blank", "noopener,noreferrer");
}

export function getTeamsAuthErrorMessage(error: unknown): string {
  const raw = error instanceof Error ? error.message : String(error);
  if (/AADSTS500011|invalid_resource|resource principal .*not found|tenant named/i.test(raw)) {
    return "Teams SSO cannot find the Sentinel API in this Teams tenant. Use the Microsoft account sign-in fallback for testing, or install/consent Sentinel in the same Entra tenant as Teams.";
  }
  if (/consent/i.test(raw)) {
    return "Teams needs admin or user consent before Sentinel can use single sign-on.";
  }
  if (/resource|webApplicationInfo|app id|application/i.test(raw)) {
    return "Teams SSO is not configured for this app package yet. Re-upload the latest Teams package or check the Entra app configuration.";
  }
  if (/not supported|not running inside/i.test(raw)) {
    return "Teams SSO is unavailable in this host. Open Sentinel in the browser to sign in.";
  }
  return raw || "Teams SSO failed. Open Sentinel in the browser to sign in.";
}