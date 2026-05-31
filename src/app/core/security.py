from __future__ import annotations

import hashlib
import hmac
import secrets


def hash_password(password: str, salt: str | None = None) -> str:
    password_bytes = password.encode("utf-8")
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password_bytes, salt_value.encode("utf-8"), 150_000)
    return f"{salt_value}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    salt, expected_hash = stored_hash.split("$", maxsplit=1)
    candidate = hash_password(password, salt).split("$", maxsplit=1)[1]
    return hmac.compare_digest(candidate, expected_hash)


def generate_token() -> str:
    return secrets.token_urlsafe(32)
