"""SQLite persistence for credentials and API keys."""

from __future__ import annotations

import os
import logging

import aiosqlite
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    encrypted_username BLOB NOT NULL,
    encrypted_password BLOB NOT NULL,
    encrypted_totp_secret BLOB
);

CREATE TABLE IF NOT EXISTS api_keys (
    key_hash TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class SessionStore:
    """Encrypted credential and API key storage backed by SQLite."""

    def __init__(self, db_path: str, encryption_key: str) -> None:
        self._db_path = db_path
        self._fernet: Fernet | None = None
        if encryption_key:
            self._fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)

    async def initialize(self) -> None:
        """Create the database and tables if they don't exist."""
        os.makedirs(os.path.dirname(self._db_path) or ".", exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(CREATE_TABLES_SQL)
            await db.commit()
        logger.info("Session store initialized at %s", self._db_path)

    def _encrypt(self, value: str) -> bytes:
        if self._fernet is None:
            raise RuntimeError("Encryption key not configured (set FTSERVICE_ENCRYPTION_KEY)")
        return self._fernet.encrypt(value.encode())

    def _decrypt(self, token: bytes) -> str:
        if self._fernet is None:
            raise RuntimeError("Encryption key not configured (set FTSERVICE_ENCRYPTION_KEY)")
        return self._fernet.decrypt(token).decode()

    # ── Credentials ──────────────────────────────────────────────

    async def save_credentials(
        self, username: str, password: str, totp_secret: str | None = None
    ) -> None:
        """Store encrypted credentials (replaces any existing)."""
        enc_user = self._encrypt(username)
        enc_pass = self._encrypt(password)
        enc_totp = self._encrypt(totp_secret) if totp_secret else None
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM credentials")
            await db.execute(
                "INSERT INTO credentials (id, encrypted_username, encrypted_password, encrypted_totp_secret) "
                "VALUES (1, ?, ?, ?)",
                (enc_user, enc_pass, enc_totp),
            )
            await db.commit()
        logger.info("Credentials saved")

    async def get_credentials(self) -> dict | None:
        """Retrieve decrypted credentials, or None if not stored."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT encrypted_username, encrypted_password, encrypted_totp_secret FROM credentials WHERE id = 1"
            ) as cursor:
                row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "username": self._decrypt(row[0]),
            "password": self._decrypt(row[1]),
            "totp_secret": self._decrypt(row[2]) if row[2] else None,
        }

    async def delete_credentials(self) -> None:
        """Remove stored credentials."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM credentials")
            await db.commit()
        logger.info("Credentials deleted")

    # ── API Keys ─────────────────────────────────────────────────

    async def save_api_key_hash(self, key_hash: str) -> None:
        """Store a hashed API key."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO api_keys (key_hash) VALUES (?)",
                (key_hash,),
            )
            await db.commit()
        logger.info("API key hash saved")

    async def validate_api_key(self, key_hash: str) -> bool:
        """Check whether a hashed API key exists in the store."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT 1 FROM api_keys WHERE key_hash = ?", (key_hash,)
            ) as cursor:
                return await cursor.fetchone() is not None
