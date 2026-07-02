import hashlib

import bcrypt

from app.core.config import settings

LEGACY_PREFIX = "sha256:"


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def _verify_legacy(password: str, password_hash: str) -> bool:
    legacy_hash = password_hash.removeprefix(LEGACY_PREFIX)
    expected = hashlib.sha256(f"{settings.secret_key}:{password}".encode()).hexdigest()
    return legacy_hash == expected


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith("$2"):
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    return _verify_legacy(password, password_hash)


def needs_password_upgrade(password_hash: str) -> bool:
    return not password_hash.startswith("$2")
