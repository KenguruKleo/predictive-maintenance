# Sentinel Intelligence Teams App

This folder contains the Microsoft Teams app package for bringing Sentinel Intelligence into Teams as a personal app tab.

## Package

- App package: `dist/sentinel-intelligence-teams-<version>.zip`
- Manifest: `manifest.json`
- Hosted Teams landing page: `frontend/public/teams.html`
- Tab URL: `https://calm-flower-0a6d7f90f.7.azurestaticapps.net/teams.html`

The zip contains only `manifest.json`, `color.png`, and `outline.png`. Teams does not host the app UI; it loads the HTTPS URL from the manifest.

For tagged releases, GitHub Actions now builds this package in a separate workflow on every `release-*` tag, validates that the tag version matches both `teamsapp/manifest.json` and `frontend/package.json`, and uploads `sentinel-intelligence-teams-<version>.zip` to the matching GitHub Release assets.

## Install In Teams

1. Open Microsoft Teams.
2. Go to **Apps** > **Manage your apps**.
3. Select **Upload an app** > **Upload a custom app**.
4. Select `teamsapp/dist/sentinel-intelligence-teams-<version>.zip`.
5. Select **Add**, then **Open**.

Custom app upload must be enabled by the tenant Teams policy.

## Authentication Status

The Teams app uses TeamsJS for the Teams-hosted sign-in path. Inside Teams, the login page calls `authentication.getAuthToken()` and sends that bearer token to the existing Azure Functions API. Browser and Electron sign-in continue to use the existing MSAL flow.

If the app is opened from a different corporate Teams tenant, Teams SSO can fail with `AADSTS500011 invalid_resource` because that tenant cannot find the Sentinel API service principal. For demos in a tenant where the Teams app cannot be approved, use the fallback button on the Teams login error card: **Open browser sign-in**. That opens Sentinel as a top-level browser app and uses the normal Sentinel Entra/MSAL flow against the project tenant.

The embedded Microsoft popup fallback was intentionally disabled for Teams-hosted tabs. Teams web and native Teams can report `CancelledByUser` before the Microsoft account is selected because the Teams iframe, Microsoft login popup, and browser storage/host popup channel do not reliably preserve the auth handoff for this cross-tenant sandbox scenario. Use top-level browser sign-in for browser demos, and use real Teams SSO only in a tenant where the Sentinel API app is installed/consented.

The Teams package includes `webApplicationInfo` for the existing Sentinel API app registration:

- Client ID: `38843d08-f211-4445-bcef-a07d383f2ee6`
- Application ID URI: `api://38843d08-f211-4445-bcef-a07d383f2ee6`

For full SSO, the Entra app registration must expose `access_as_user`, allow the Microsoft Teams client applications as authorized clients, and assign Sentinel app roles to the user or group. If SSO is not ready, the login page shows an explicit error and can open Sentinel in the browser instead of silently stalling inside the iframe.

Current tenant configuration checked on 2026-04-28:

- `access_as_user` is exposed on `sentinel-intelligence-api`.
- `requestedAccessTokenVersion` is set to `2`.
- The Teams desktop/mobile and Teams web client IDs are pre-authorized for the API scope.
- The documented demo user has Sentinel app roles in the issued API token.

Teams client IDs to pre-authorize for the exposed API scope:

- Teams desktop/mobile: `1fec8e78-bce4-4aaf-ab1b-5451cc387264`
- Teams web: `5e3ce6c0-2b1f-4285-8d4b-75ee78787346`

Microsoft's current Teams SSO docs recommend an Application ID URI shaped like `api://<tab-domain>/<app-id>`. This project currently uses the existing deployed API audience `api://38843d08-f211-4445-bcef-a07d383f2ee6`; if the Entra app is changed to a domain-based URI later, update the Teams manifest, frontend API scopes, and backend `ENTRA_API_AUDIENCE` together.

## Before Publishing Updates

Deploy the frontend after changing Teams landing pages or Static Web Apps headers:

```bash
cd frontend
npm run build
swa deploy ./dist --deployment-token "$SWA_DEPLOYMENT_TOKEN"
```

If Teams shows a blank frame or a refused-to-connect message, confirm that the deployed Static Web App no longer sends `X-Frame-Options: DENY` and that the `Content-Security-Policy` header includes Teams in `frame-ancestors`.

## Rebuild Package

```bash
node teamsapp/scripts/generate-icons.mjs
cd teamsapp
mkdir -p dist
VERSION=0.3.3
zip -j "dist/sentinel-intelligence-teams-${VERSION}.zip" manifest.json color.png outline.png
```

If you change `manifest.json`, increment `version` before re-uploading the package.
