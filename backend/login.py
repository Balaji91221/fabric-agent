"""One-shot device-code login for Microsoft Fabric.

Run it yourself:   python3 backend/login.py

Signs you in as *your own* Entra ID user (no service principal, no client
secret) and caches the token in .fabric_token with mode 600. Row-level
security applies, because the token carries your identity.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = ROOT / ".fabric_token"

SCOPE = "https://analysis.windows.net/powerbi/api/.default offline_access"
# Public first-party clients that are pre-consented in most tenants.
# Azure CLI first; Power BI's own client is the fallback when Conditional
# Access blocks the CLI.
CLIENTS = [
    ("Azure CLI", "04b07795-8ddb-461a-bbee-02f9e1bf7b46"),
    ("Power BI", "871c010f-5e61-4fb1-83ac-98610a7e9110"),
]


def _tenant_id() -> str:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("FABRIC_TENANT_ID=") and not line.startswith("#"):
                value = line.split("=", 1)[1].strip()
                if value:
                    return value
    value = os.getenv("FABRIC_TENANT_ID", "").strip()
    if value:
        return value
    sys.exit("No FABRIC_TENANT_ID in .env or environment.")


def _post(url: str, fields: dict[str, str]) -> tuple[int, dict]:
    body = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=body)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except ValueError:
            return exc.code, {"error": "http_error", "error_description": raw[:300].decode()}


def _authorize(tenant: str, client_id: str, label: str) -> dict | None:
    base = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"

    status, start = _post(f"{base}/devicecode", {"client_id": client_id, "scope": SCOPE})
    if status != 200:
        print(f"  {label}: cannot start device login — {start.get('error_description', start)[:200]}")
        return None

    print()
    print(f"  Signing in with the {label} public client.")
    print(f"  1. Open  {start['verification_uri']}")
    print(f"  2. Code  {start['user_code']}")
    print(f"     (expires in {start['expires_in'] // 60} minutes)")
    print()
    print("  Waiting for you to approve in the browser...", flush=True)

    interval = int(start.get("interval", 5))
    deadline = time.time() + int(start.get("expires_in", 900))

    while time.time() < deadline:
        time.sleep(interval)
        status, payload = _post(
            f"{base}/token",
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": client_id,
                "device_code": start["device_code"],
            },
        )
        if status == 200:
            return payload

        error = payload.get("error", "")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        if error == "expired_token":
            print("  Code expired before it was approved.")
            return None
        # authorization_declined, or a Conditional Access block.
        print(f"  {label}: {error} — {payload.get('error_description', '')[:220]}")
        return None

    print("  Timed out waiting for approval.")
    return None


def main() -> int:
    tenant = _tenant_id()
    print(f"\n  Tenant {tenant}")

    token = None
    for label, client_id in CLIENTS:
        token = _authorize(tenant, client_id, label)
        if token:
            used_client = client_id
            break
        print("  Trying the next client...\n")

    if not token:
        print("\n  Login failed. Nothing was saved.\n")
        return 1

    token["obtained_at"] = time.time()
    token["client_id"] = used_client
    token["tenant_id"] = tenant

    TOKEN_FILE.write_text(json.dumps(token))
    TOKEN_FILE.chmod(0o600)

    expires_in = int(token.get("expires_in", 0))
    print()
    print(f"  Signed in. Token saved to {TOKEN_FILE.name} (mode 600).")
    print(f"  Access token valid {expires_in // 60} min.")
    print(f"  Refresh token: {'yes' if token.get('refresh_token') else 'no'}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
