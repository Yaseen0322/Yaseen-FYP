"""
Helpers for encrypting and decrypting sensitive JSON payloads persisted in the database.
"""
import base64
import hashlib
import json
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken

from .config import settings


def _get_fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_json_payload(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    if not payload:
        return {}

    ciphertext = _get_fernet().encrypt(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).decode("utf-8")
    return {
        "__encrypted__": True,
        "ciphertext": ciphertext,
    }


def decrypt_json_payload(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    if not payload:
        return {}

    if not payload.get("__encrypted__"):
        return payload

    ciphertext = payload.get("ciphertext")
    if not ciphertext:
        return {}

    try:
        decrypted = _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return {}

    return json.loads(decrypted)
