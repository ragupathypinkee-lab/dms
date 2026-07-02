STATUS_FLOW: list[tuple[str, str]] = [
    ("collecting", "需求收集"),
    ("ai_evaluating", "AI评估"),
    ("approving", "立项中"),
    ("agent_design", "Agent设计"),
    ("developing", "开发中"),
    ("testing", "测试中"),
    ("launched", "已上线"),
]

STATUS_LABELS = dict(STATUS_FLOW)
STATUS_ORDER = [key for key, _ in STATUS_FLOW]

LEGACY_STATUS_MAP = {
    "pending": "collecting",
    "evaluating": "collecting",
    "analyzing": "ai_evaluating",
    "in_progress": "developing",
    "done": "launched",
    "completed": "launched",
}

# 首页统计卡片分组（兼容历史状态值）
STAT_COLLECTING_STATUSES = ("collecting", "evaluating", "pending", "ai_evaluating")
STAT_DEVELOPING_STATUSES = (
    "developing",
    "in_progress",
    "approving",
    "agent_design",
    "testing",
)
STAT_LAUNCHED_STATUSES = ("launched", "completed", "done")


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
