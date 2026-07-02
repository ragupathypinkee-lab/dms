from collections import defaultdict
from time import time

_attempts: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(key: str, *, max_attempts: int = 5, window_seconds: int = 300) -> bool:
    now = time()
    attempts = [t for t in _attempts[key] if now - t < window_seconds]
    if len(attempts) >= max_attempts:
        _attempts[key] = attempts
        return False
    attempts.append(now)
    _attempts[key] = attempts
    return True


def reset_rate_limit(key: str) -> None:
    _attempts.pop(key, None)
