# T-056 — Electron desktop app shell

**Priority:** Medium  
**Status:** Done  
**Depends on:** T-030, T-032, T-033

## Problem

The operator console is currently web-only. During live incident monitoring, users need native desktop affordances that continue to work when the browser is in the background: an unread badge and native notifications for new incident events.

## Goal

Wrap the existing React/Vite frontend in a lightweight Electron shell without changing the web deployment path. The desktop build should reuse the same UI and SignalR notification flow while exposing only narrow native APIs through a preload bridge.

## Scope

- Add Electron development/runtime scripts to the frontend package.
- Add a secure Electron main process and preload bridge.
- Reflect the unread notification count in the native app badge.
- Send native desktop notifications from SignalR incident events.
- Keep the web build working without Electron globals.

## Implementation notes

- Electron loads the Vite dev server in development and `dist/index.html` after build.
- Renderer code accesses native features only through `window.sentinelDesktop` from preload.
- Badge updates are driven by the same `unreadCount` used by the in-app notification center.
- Native notifications are best-effort; browser notifications remain the web fallback.

## Definition of Done

- [x] Electron package scripts and main entry are added.
- [x] `frontend/electron/` contains main and preload bridge files.
- [x] `AppShell` updates the native unread badge.
- [x] `useSignalR` sends native notifications for important incident events.
- [x] Frontend build passes.
- [x] Lint passes.