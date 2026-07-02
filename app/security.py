import hashlib

from app.config import settings


def hash_password(password: str) -> str:
    return hashlib.sha256(f"{settings.secret_key}:{password}".encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash
