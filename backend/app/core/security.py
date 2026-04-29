from __future__ import annotations

import hmac
import hashlib


def verify_github_signature(*, secret: str, body: bytes, signature_header: str | None) -> bool:
    if not secret:
        return False
    if not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    their_sig = signature_header.removeprefix("sha256=")
    mac = hmac.new(secret.encode("utf-8"), msg=body, digestmod=hashlib.sha256)
    our_sig = mac.hexdigest()
    return hmac.compare_digest(our_sig, their_sig)
