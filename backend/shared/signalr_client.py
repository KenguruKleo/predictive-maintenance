"""
SignalR REST client — send real-time push notifications via Azure SignalR Service (T-030).

Uses the SignalR Service Management REST API directly (no extra SDK dependency).
Authentication: JWT token signed with the connection string AccessKey.

Usage:
    from shared.signalr_client import notify_signalr_sync

    notify_signalr_sync(
        hub="deviationHub",
        event="incident_pending_approval",
        payload={"incident_id": "inc-001", "equipment_id": "GR-204", "risk_level": "high", "created_at": "..."},
        target_role="operator",
    )
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)
DEFAULT_HUB = "deviationHub"


def _parse_connection_string(conn_str: str) -> tuple[str, str]:
    """Parse 'Endpoint=https://...;AccessKey=...;Version=1.0;' → (endpoint, access_key)."""
    parts: dict[str, str] = {}
    for part in conn_str.split(";"):
        if "=" in part:
            key, _, val = part.partition("=")
            parts[key.strip()] = val.strip()
    endpoint = parts.get("Endpoint", "").rstrip("/")
    access_key = parts.get("AccessKey", "")
    return endpoint, access_key


def _generate_jwt(audience: str, access_key: str, ttl: int = 1800) -> str:
    """
    Generate a JWT for authenticating with the SignalR Service Management REST API.

    audience: full URL of the API endpoint (used as 'aud' claim)
    access_key: HMAC-SHA256 signing key from the connection string
    ttl: token lifetime in seconds (default 30 min)
    """
    now = int(time.time())
    header = (
        base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        .rstrip(b"=")
        .decode()
    )
    claims = {"aud": audience, "iat": now, "exp": now + ttl}
    payload = (
        base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    )
    signing_input = f"{header}.{payload}"
    sig = (
        base64.urlsafe_b64encode(
            hmac.new(
                access_key.encode(), signing_input.encode(), hashlib.sha256
            ).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    return f"{signing_input}.{sig}"


def notify_signalr_sync(
    hub: str,
    event: str,
    payload: dict,
    target_role: str | None = None,
    incident_id: str | None = None,
) -> bool:
    """
    Send a SignalR push notification synchronously (safe to call from Durable activities).

    Routing priority:
      target_role  → sends to group "role:{target_role}"
      incident_id  → additionally sends to group "incident:{incident_id}"
      neither      → broadcasts to all connections on the hub

    Returns True if all sends succeeded.
    """
    conn_str = os.getenv("AzureSignalRConnectionString", "")
    if not conn_str:
        logger.warning(
            "AzureSignalRConnectionString not configured — SignalR push skipped"
        )
        return False

    endpoint, access_key = _parse_connection_string(conn_str)
    if not endpoint or not access_key:
        logger.warning("Invalid SignalR connection string — SignalR push skipped")
        return False

    body = json.dumps({"target": event, "arguments": [payload]}).encode()

    # Collect target URLs; URL-encode group names to handle colons
    urls: list[str] = []
    if target_role:
        group = urllib.parse.quote(f"role:{target_role}", safe="")
        urls.append(f"{endpoint}/api/v1/hubs/{hub}/groups/{group}")
    if incident_id:
        group = urllib.parse.quote(f"incident:{incident_id}", safe="")
        urls.append(f"{endpoint}/api/v1/hubs/{hub}/groups/{group}")
    if not urls:
        # Broadcast to all connected clients
        urls.append(f"{endpoint}/api/v1/hubs/{hub}")

    success = True
    for url in urls:
        token = _generate_jwt(url, access_key)
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                logger.debug("SignalR push '%s' → %s OK", event, url)
        except urllib.error.HTTPError as exc:
            logger.error(
                "SignalR push failed to %s: HTTP %d %s", url, exc.code, exc.reason
            )
            success = False
        except Exception:
            logger.exception("SignalR push unexpected error to %s", url)
            success = False

    return success


def add_connection_to_group_sync(
    connection_id: str,
    group_name: str,
    *,
    hub: str = DEFAULT_HUB,
) -> bool:
    """Add a connected SignalR client to a named group."""
    if not connection_id or not group_name:
        return False

    conn_str = os.getenv("AzureSignalRConnectionString", "")
    if not conn_str:
        logger.warning(
            "AzureSignalRConnectionString not configured — SignalR group registration skipped"
        )
        return False

    endpoint, access_key = _parse_connection_string(conn_str)
    if not endpoint or not access_key:
        logger.warning("Invalid SignalR connection string — group registration skipped")
        return False

    group = urllib.parse.quote(group_name, safe="")
    encoded_connection_id = urllib.parse.quote(connection_id, safe="")
    url = (
        f"{endpoint}/api/v1/hubs/{hub}/groups/{group}"
        f"/connections/{encoded_connection_id}"
    )

    token = _generate_jwt(url, access_key)
    req = urllib.request.Request(
        url,
        data=b"",
        headers={"Authorization": f"Bearer {token}"},
        method="PUT",
    )

    try:
        with urllib.request.urlopen(req, timeout=10):
            logger.debug(
                "SignalR group registration succeeded: connection=%s group=%s",
                connection_id,
                group_name,
            )
            return True
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            logger.debug(
                "SignalR group registration already exists: connection=%s group=%s",
                connection_id,
                group_name,
            )
            return True
        logger.error(
            "SignalR group registration failed to %s: HTTP %d %s",
            url,
            exc.code,
            exc.reason,
        )
    except Exception:
        logger.exception("SignalR group registration unexpected error to %s", url)

    return False
