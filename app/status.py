STATUS_FLOW: list[tuple[str, str]] = [
    ("evaluating", "待评估"),
    ("analyzing", "分析中"),
    ("developing", "开发中"),
    ("testing", "测试中"),
    ("completed", "已完成"),
]

STATUS_LABELS = dict(STATUS_FLOW)
STATUS_ORDER = [key for key, _ in STATUS_FLOW]

LEGACY_STATUS_MAP = {
    "pending": "evaluating",
    "in_progress": "developing",
    "done": "completed",
}


def normalize_status(status: str) -> str:
    return LEGACY_STATUS_MAP.get(status, status)


def get_status_label(status: str) -> str:
    normalized = normalize_status(status)
    return STATUS_LABELS.get(normalized, status)


def validate_status(status: str) -> str:
    normalized = normalize_status(status)
    if normalized not in STATUS_ORDER:
        raise ValueError(f"无效状态: {status}")
    return normalized
