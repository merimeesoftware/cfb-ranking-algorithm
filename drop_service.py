"""The Drop email subscribe — webhook to ESP when configured, else accept + log."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Tuple

# RFC 5321 maximum. Cap length before matching so a hostile payload cannot
# force polynomial backtracking. The dot is literal and excluded from the
# repeated label class, so each character has one way to match.
_EMAIL_MAX_LEN = 254
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


def validate_email(email: str) -> bool:
    if not email or not isinstance(email, str):
        return False
    cleaned = email.strip()
    if not cleaned or len(cleaned) > _EMAIL_MAX_LEN:
        return False
    return EMAIL_RE.match(cleaned) is not None


def subscribe_to_drop(email: str, source: str = "web") -> Tuple[int, Dict[str, Any]]:
    """
    Returns (status_code, payload).

    Production: set DROP_WEBHOOK_URL to a Buttondown/Mailchimp/Beehiiv webhook.
    Dev/offline: accept valid emails without storing PII on disk.
    """
    cleaned = (email or "").strip().lower()
    if not validate_email(cleaned):
        return 400, {"error": "Enter a valid email."}

    webhook = os.environ.get("DROP_WEBHOOK_URL", "").strip()
    if webhook:
        body = json.dumps({"email": cleaned, "source": source, "list": "the-drop"}).encode("utf-8")
        req = urllib.request.Request(
            webhook,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    return 502, {"error": "Newsletter provider rejected the signup."}
        except urllib.error.HTTPError:
            return 502, {"error": "Newsletter provider rejected the signup."}
        except Exception:
            return 502, {"error": "Could not reach newsletter provider."}

    return 200, {
        "message": "You're on The Drop. Same free rankings as the site.",
        "email": cleaned,
        "mode": "webhook" if webhook else "accepted",
    }
