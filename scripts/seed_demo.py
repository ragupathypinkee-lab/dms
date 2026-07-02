"""演示/测试数据：以 AI 需求登记系统业务场景为例。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.models import Demand, User  # noqa: E402

# admin 必须在 DEFAULT_USERS 中第一个创建，保证 id=1
DEMO_USERS: tuple[tuple[str, str], ...] = (
    ("zhangsan", "123456"),
    ("lisi", "123456"),
    ("wangwu", "123456"),
    ("zhaoliu", "123456"),
    ("chenxi", "123456"),
    ("product_mgr", "123456"),
)

DEMO_DEMANDS: tuple[dict, ...] = (
    {
        "username": "zhangsan",
        "title": "智能客服对话机器人",
        "description": "建设基于大模型的在线客服系统，支持多轮对话、意图识别与工单自动创建，降低人工客服压力。",
        "department": "产品部",
        "priority": "high",
        "status": "analyzing",
    },
    {
        "username": "lisi",
        "title": "OCR 发票识别自动化",
        "description": "对接财务报销流程，自动识别增值税发票字段并校验真伪，减少手工录入错误。",
        "department": "财务部",
        "priority": "high",
        "status": "developing",
    },
    {
        "username": "wangwu",
        "title": "销售线索智能评分",
        "description": "根据客户行为、行业与历史成交数据，对 CRM 线索进行 AI 评分，辅助销售 prioritization。",
        "department": "销售部",
        "priority": "medium",
        "status": "evaluating",
    },
    {
        "username": "zhangsan",
        "title": "代码审查 AI 助手",
        "description": "在 GitLab MR 流程中集成 AI Code Review，自动发现安全漏洞、性能问题与规范违规。",
        "department": "研发部",
        "priority": "high",
        "status": "testing",
    },
    {
        "username": "admin",
        "title": "PRD 文档自动生成",
        "description": "输入需求要点后，AI 自动生成标准 PRD 模板，包含用户故事、验收标准与非功能需求章节。",
        "department": "产品部",
        "priority": "medium",
        "status": "completed",
    },
    {
        "username": "user",
        "title": "移动端需求登记体验优化",
        "description": "优化小屏下的卡片布局、状态切换与 AI 分析交互，提升业务方外出登记需求的效率。",
        "department": "研发部",
        "priority": "medium",
        "status": "developing",
    },
    {
        "username": "zhaoliu",
        "title": "企业知识库问答系统",
        "description": "整合制度文档、FAQ 与产品手册，提供自然语言检索与精准引用，支持权限隔离。",
        "department": "运营部",
        "priority": "low",
        "status": "evaluating",
    },
    {
        "username": "lisi",
        "title": "会议纪要自动摘要",
        "description": "对线上会议录音转写并生成结构化纪要，自动提取待办事项与负责人。",
        "department": "行政部",
        "priority": "low",
        "status": "analyzing",
    },
    {
        "username": "wangwu",
        "title": "库存预测补货模型",
        "description": "基于历史销量、季节性与促销计划，预测各 SKU 未来 4 周需求量并给出补货建议。",
        "department": "供应链部",
        "priority": "high",
        "status": "developing",
    },
    {
        "username": "product_mgr",
        "title": "用户画像标签体系",
        "description": "构建 AI 驱动的用户标签自动打标 pipeline，支持营销分群与个性化推荐。",
        "department": "数据部",
        "priority": "medium",
        "status": "testing",
    },
    {
        "username": "zhaoliu",
        "title": "AI 新人培训助手",
        "description": "为 HR 提供可对话的新员工培训助手，覆盖制度问答、流程引导与学习测验。",
        "department": "人力资源部",
        "priority": "low",
        "status": "evaluating",
    },
    {
        "username": "admin",
        "title": "合同条款风险识别",
        "description": "上传合同 PDF 后自动标注高风险条款（违约责任、知识产权、数据合规等）并给出修改建议。",
        "department": "法务部",
        "priority": "high",
        "status": "analyzing",
    },
    {
        "username": "chenxi",
        "title": "竞品情报自动采集",
        "description": "定期抓取竞品官网、应用商店与社媒动态，AI 汇总功能变化与市场动作周报。",
        "department": "市场部",
        "priority": "medium",
        "status": "evaluating",
    },
    {
        "username": "chenxi",
        "title": "营销文案 A/B 测试生成",
        "description": "根据产品卖点与目标人群，批量生成多版本广告文案并预估点击率，供投放团队选用。",
        "department": "市场部",
        "priority": "high",
        "status": "developing",
    },
    {
        "username": "product_mgr",
        "title": "需求优先级 AI 辅助评估",
        "description": "结合业务价值、技术复杂度与资源排期，对需求池进行智能优先级排序与冲突提醒。",
        "department": "产品部",
        "priority": "high",
        "status": "completed",
    },
    {
        "username": "user",
        "title": "需求状态变更通知推送",
        "description": "当需求状态变更时，通过企业微信/邮件通知提交人与相关干系人，减少信息滞后。",
        "department": "研发部",
        "priority": "low",
        "status": "testing",
    },
    {
        "username": "wangwu",
        "title": "客户流失预警模型",
        "description": "识别高流失风险客户并推送挽回策略建议，与销售 CRM 工作流联动。",
        "department": "销售部",
        "priority": "medium",
        "status": "completed",
    },
    {
        "username": "lisi",
        "title": "费用报销异常检测",
        "description": "利用 AI 检测报销单中的异常模式（重复报销、超标、虚假发票），降低财务风险。",
        "department": "财务部",
        "priority": "medium",
        "status": "testing",
    },
)

SAMPLE_AI_ANALYSIS = """一、需求理解
该需求目标明确，符合企业 AI 落地场景，建议先明确 MVP 范围与验收指标。

二、风险
1. 数据质量与权限边界需提前确认
2. 模型效果需业务方参与评测
3. 与现有系统集成存在排期依赖

三、开发工作量
预估 5–10 人天（含联调测试），若涉及外部 API 对接可能延长至 2–3 周。

四、建议
1. 先做小范围试点验证效果
2. 补充异常流程与降级方案
3. 制定上线后效果评估指标"""


def _ensure_demo_users(db: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    for row in db.scalars(select(User)).all():
        users[row.username] = row

    for username, password in DEMO_USERS:
        if username not in users:
            user = User(
                username=username,
                password_hash=hash_password(password),
                role="user",
            )
            db.add(user)
            db.flush()
            users[username] = user

    db.commit()
    for row in db.scalars(select(User)).all():
        users[row.username] = row
    return users


def seed_demo_data(db: Session, *, replace_demands: bool = True) -> dict[str, int]:
    users = _ensure_demo_users(db)

    admin = db.scalar(select(User).where(User.username == "admin"))
    if admin is None:
        raise RuntimeError("admin 用户不存在，请先执行 init_db()")

    if replace_demands:
        db.execute(delete(Demand))
        db.commit()

    existing_count = db.scalar(select(func.count()).select_from(Demand))
    if existing_count and not replace_demands:
        return {
            "users": len(users),
            "demands": existing_count,
            "skipped": 1,
        }

    created = 0
    for index, item in enumerate(DEMO_DEMANDS):
        owner = users.get(item["username"])
        if owner is None:
            continue
        db.add(
            Demand(
                user_id=owner.id,
                title=item["title"],
                description=item["description"],
                department=item["department"],
                priority=item["priority"],
                status=item["status"],
                creator=owner.username,
                ai_analysis=SAMPLE_AI_ANALYSIS if index % 3 == 0 else None,
            )
        )
        created += 1

    db.commit()
    return {"users": len(users), "demands": created, "skipped": 0}


def run_seed_demo(*, replace_demands: bool = True) -> dict[str, int]:
    from app.db.session import SessionLocal, init_db

    init_db()
    with SessionLocal() as db:
        return seed_demo_data(db, replace_demands=replace_demands)


if __name__ == "__main__":
    result = run_seed_demo(replace_demands=True)
    print(
        f"演示数据写入完成：{result['users']} 个用户，{result['demands']} 条需求"
        + ("（已跳过，需求已存在）" if result.get("skipped") else "")
    )
