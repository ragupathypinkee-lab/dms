import re

from fastapi import HTTPException

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{2,50}$")
PRIORITIES = frozenset({"high", "medium", "low"})

PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 128
TITLE_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 10000
CREATOR_MAX_LENGTH = 100
REMARK_MAX_LENGTH = 200
DEPARTMENT_NAME_MAX_LENGTH = 100
SORT_ORDER_MAX = 9999
AI_ANALYSIS_MAX_LENGTH = 50000


class ValidationError(ValueError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def validate_username(username: str) -> str:
    username = username.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValidationError("用户名仅支持 2–50 位字母、数字或下划线")
    return username


def validate_login_password(password: str) -> str:
    if not password:
        raise ValidationError("请输入密码")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValidationError(f"密码不能超过 {PASSWORD_MAX_LENGTH} 位")
    return password


def validate_password(password: str) -> str:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationError(f"密码至少 {PASSWORD_MIN_LENGTH} 位")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValidationError(f"密码不能超过 {PASSWORD_MAX_LENGTH} 位")
    return password


def validate_priority(priority: str) -> str:
    priority = priority.strip()
    if priority not in PRIORITIES:
        raise ValidationError("无效的优先级")
    return priority


def validate_optional_priority(priority: str | None) -> str | None:
    if not priority:
        return None
    return validate_priority(priority)


def validate_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise ValidationError("需求标题不能为空")
    if len(title) > TITLE_MAX_LENGTH:
        raise ValidationError(f"需求标题不能超过 {TITLE_MAX_LENGTH} 字")
    return title


def validate_description(description: str) -> str:
    description = description.strip()
    if not description:
        raise ValidationError("需求描述不能为空")
    if len(description) > DESCRIPTION_MAX_LENGTH:
        raise ValidationError(f"需求描述不能超过 {DESCRIPTION_MAX_LENGTH} 字")
    return description


def validate_creator(creator: str) -> str:
    creator = creator.strip()
    if not creator:
        raise ValidationError("创建人不能为空")
    if len(creator) > CREATOR_MAX_LENGTH:
        raise ValidationError(f"创建人不能超过 {CREATOR_MAX_LENGTH} 字")
    return creator


def validate_remark(remark: str) -> str:
    remark = remark.strip()
    if not remark:
        raise ValidationError("请填写变更备注")
    if len(remark) > REMARK_MAX_LENGTH:
        raise ValidationError(f"备注不能超过 {REMARK_MAX_LENGTH} 字")
    return remark


def validate_department_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValidationError("单位名称不能为空")
    if len(name) > DEPARTMENT_NAME_MAX_LENGTH:
        raise ValidationError(f"单位名称不能超过 {DEPARTMENT_NAME_MAX_LENGTH} 字")
    return name


def validate_sort_order(sort_order: int) -> int:
    if sort_order < 0 or sort_order > SORT_ORDER_MAX:
        raise ValidationError(f"排序值需在 0–{SORT_ORDER_MAX} 之间")
    return sort_order


def validate_optional_text(value: str | None, *, max_length: int) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) > max_length:
        raise ValidationError(f"内容不能超过 {max_length} 字")
    return value


def raise_http_validation(exc: ValidationError) -> None:
    raise HTTPException(status_code=400, detail=exc.message) from exc
