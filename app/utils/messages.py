FLASH_MESSAGES: dict[str, tuple[str, str]] = {
    "created": ("success", "AI 需求提交成功，已进入需求收集阶段"),
    "updated": ("success", "需求信息更新成功"),
    "deleted": ("success", "需求已删除"),
    "status_updated": ("success", "智能体孵化状态更新成功"),
    "forbidden": ("danger", "无权操作该需求"),
    "invalid_status": ("danger", "无效的状态值"),
    "ai_analyzed": ("success", "AI 可行性评估完成"),
    "ai_analyze_failed": ("danger", "AI 评估失败，请稍后重试"),
    "user_created": ("success", "用户创建成功"),
    "user_exists": ("danger", "用户名已存在"),
    "user_password_short": ("danger", "密码至少 6 位"),
    "admin_forbidden": ("danger", "仅管理员可操作"),
    "password_updated": ("success", "密码修改成功"),
    "password_wrong": ("danger", "当前密码不正确"),
    "password_mismatch": ("danger", "两次输入的新密码不一致"),
    "department_created": ("success", "单位创建成功"),
    "department_updated": ("success", "单位更新成功"),
    "department_deleted": ("success", "单位已删除"),
    "department_exists": ("danger", "单位名称已存在"),
    "department_in_use": ("danger", "该单位下仍有关联需求，无法删除"),
    "no_department": ("danger", "请先联系信息化管理部门配置单位"),
    "invalid_department": ("danger", "无效的申请单位"),
    "status_remark_required": ("danger", "请填写变更备注"),
    "status_remark_too_long": ("danger", "变更备注不能超过 200 字"),
    "csrf_failed": ("danger", "请求已过期，请刷新页面后重试"),
    "login_rate_limited": ("danger", "登录尝试过于频繁，请稍后再试"),
    "validation_error": ("danger", "提交内容不符合要求"),
}


def get_flash_message(msg_key: str | None) -> dict[str, str] | None:
    if not msg_key or msg_key not in FLASH_MESSAGES:
        return None
    level, text = FLASH_MESSAGES[msg_key]
    return {"level": level, "text": text}
