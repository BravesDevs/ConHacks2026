from __future__ import annotations

import hmac
import hashlib

from cryptography.fernet import Fernet


def verify_github_signature(
    *, secret: str, body: bytes, signature_header: str | None
) -> bool:
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


def _fernet() -> Fernet:
    from app.core.config import get_settings

    key = get_settings().github_token_encryption_key
    if not key:
        raise RuntimeError("github_token_encryption_key is not configured")
    return Fernet(key.encode("utf-8"))


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
