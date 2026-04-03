"""API key generation and validation."""

from __future__ import annotations

import hashlib
import secrets


def generate_api_key() -> str:
    """Generate a new random API key."""
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """SHA-256 hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


async def validate_api_key(key: str, store) -> bool:
    """Validate an API key against the store."""
    key_hash = hash_api_key(key)
    return await store.validate_api_key(key_hash)
