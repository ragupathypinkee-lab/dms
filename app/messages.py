FLASH_MESSAGES: dict[str, tuple[str, str]] = {
    "created": ("success", "需求登记成功"),
    "updated": ("success", "需求更新成功"),
    "deleted": ("success", "需求已删除"),
    "status_updated": ("success", "状态更新成功"),
    "forbidden": ("danger", "无权操作该需求"),
    "invalid_status": ("danger", "无效的状态值"),
    "ai_analyzed": ("success", "AI 分析完成"),
    "user_created": ("success", "用户创建成功"),
    "user_exists": ("danger", "用户名已存在"),
    "user_password_short": ("danger", "密码至少 4 位"),
    "admin_forbidden": ("danger", "仅管理员可操作"),
    "password_updated": ("success", "密码修改成功"),
    "password_wrong": ("danger", "当前密码不正确"),
    "password_mismatch": ("danger", "两次输入的新密码不一致"),
}


def get_flash_message(msg_key: str | None) -> dict[str, str] | None:
    if not msg_key or msg_key not in FLASH_MESSAGES:
        return None
    level, text = FLASH_MESSAGES[msg_key]
    return {"level": level, "text": text}
