# T-056 — Electron desktop app shell

**Priority:** Medium  
**Status:** Done  
**Depends on:** T-030, T-032, T-033

## Problem

The operator console was web-only. During live incident monitoring, users need native desktop affordances that continue to work when the browser is in the background: an unread badge and native notifications for new incident events. In production, a shop-floor operator console should not depend only on an open browser tab; a desktop app gives the system a more reliable day-to-day surface on Windows/macOS/Linux workstations.

## Goal

Wrap the existing React/Vite frontend in a lightweight multi-platform Electron shell without changing the web deployment path. The desktop build reuses the same UI and SignalR notification flow while exposing only narrow native APIs through a preload bridge.

## Scope

- Add Electron development/runtime scripts to the frontend package.
- Add a secure Electron main process and preload bridge.
- Reflect the unread notification count in the native app badge.
- Send native desktop notifications from SignalR incident events.
- Keep the web build working without Electron globals.
- Use `localhost` for Electron development auth so Entra redirect URIs match literally.
- Keep the desktop renderer alive when the operator closes the window chrome, so SignalR can continue receiving incident notifications in the background.
- Package macOS DMG/ZIP artifacts in CI and publish them to GitHub Releases for `v*` tags.

## Implementation notes

- Electron loads the Vite dev server in development and `dist/index.html` after build.
- Renderer code accesses native features only through `window.sentinelDesktop` from preload.
- Badge updates are driven by the same `unreadCount` used by the in-app notification center.
- Native notifications are best-effort; browser notifications remain the web fallback.
- Desktop auth uses the MSAL local-storage cache and a persistent Electron session; web auth keeps the existing session-storage behavior.
- Packaged desktop builds serve the renderer from a local `http://localhost:5173` static server instead of `file://`, keeping Entra/MSAL redirect behavior compatible with the development app registration.
- Closing the desktop window hides it instead of destroying the renderer. A real quit still exits the app.
- Future desktop channels can reuse the same notification abstraction for Teams or other collaboration integrations.

## Definition of Done

- [x] Electron package scripts and main entry are added.
- [x] `frontend/electron/` contains main and preload bridge files.
- [x] `AppShell` updates the native unread badge.
- [x] `useSignalR` sends native notifications for important incident events.
- [x] Frontend build passes.
- [x] Lint passes.
- [x] Electron interactive login works through `http://localhost:5173`.
- [x] Live incident notification path was verified with a newly simulated alert.
- [x] Desktop auth cache persists across renderer restarts where MSAL can silently reuse the cached account.
- [x] Closing the Electron window keeps the app process and SignalR renderer alive in the background.
- [x] GitHub Actions macOS packaging workflow uploads DMG/ZIP artifacts and attaches them to `v*` releases.
