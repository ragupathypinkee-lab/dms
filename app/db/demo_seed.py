"""首次启动演示数据：8 条校园 AI 智能体场景。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Demand, User
from app.services.department import get_or_create_department
from app.services.status_log import record_status_change

DEMO_DEMANDS: tuple[dict, ...] = (
    {
        "username": "admin",
        "title": "AI 排课助手",
        "description": "面向教务管理人员，基于培养方案与教室资源智能生成排课建议，自动检测冲突并解答排课规则咨询。",
        "department": "教务处",
        "priority": "high",
        "status": "collecting",
    },
    {
        "username": "admin",
        "title": "AI 招生咨询",
        "description": "为考生及家长提供 7×24 小时招生政策、专业介绍、录取分数线等自然语言咨询服务，减轻招生办高峰压力。",
        "department": "招生办",
        "priority": "high",
        "status": "launched",
    },
    {
        "username": "user",
        "title": "AI 图书问答",
        "description": "支持师生以自然语言检索馆藏与电子资源，推荐相关文献并生成阅读摘要，提升科研与教学文献获取效率。",
        "department": "图书馆",
        "priority": "medium",
        "status": "testing",
    },
    {
        "username": "user",
        "title": "AI 财务报销助手",
        "description": "对接财务报销系统，自动识别发票字段、校验真伪并引导填写报销单，减少师生手工录入与财务审核工作量。",
        "department": "财务处",
        "priority": "high",
        "status": "developing",
    },
    {
        "username": "admin",
        "title": "AI 科研助手",
        "description": "辅助教师撰写科研项目申报书，自动匹配资助政策、生成研究摘要并检查材料完整性，提升科研处管理效率。",
        "department": "科研处",
        "priority": "medium",
        "status": "ai_evaluating",
    },
    {
        "username": "user",
        "title": "AI 请假审批助手",
        "description": "学生通过对话提交请假申请，智能体自动核验课表冲突与请假政策，辅助学生处完成初审与流程引导。",
        "department": "学生处",
        "priority": "medium",
        "status": "approving",
    },
    {
        "username": "admin",
        "title": "AI 宿舍报修助手",
        "description": "师生描述报修问题后，智能体自动分类故障类型、估算紧急程度并分派至后勤相应班组，跟踪处理进度。",
        "department": "后勤处",
        "priority": "high",
        "status": "agent_design",
    },
    {
        "username": "user",
        "title": "AI 教学督导助手",
        "description": "汇总课堂巡课记录与教学评价数据，自动生成督导分析报告与改进建议，辅助教务处教学质量监控。",
        "department": "教务处",
        "priority": "medium",
        "status": "collecting",
    },
)

SAMPLE_AI_ANALYSIS = """一、需求理解
该 AI 应用场景目标明确，符合高校信息化建设方向，建议先明确智能体 MVP 范围与师生验收指标。

二、风险
1. 校园数据权限与隐私合规需提前确认
2. 智能体效果需业务单位参与评测
3. 与现有教务/学工/财务等系统集成存在排期依赖

三、开发工作量
预估 8–15 人天（含 Agent 设计、联调测试），若涉及校园统一身份认证对接可能延长至 3–4 周。

四、建议
1. 先做小范围试点验证智能体效果
2. 补充异常流程与人工兜底方案
3. 制定上线后服务满意度与效率提升评估指标"""


def seed_demo_demands_if_empty(db: Session) -> int:
    """数据库无需求记录时写入演示数据，返回新建条数。"""
    existing = db.scalar(select(func.count()).select_from(Demand)) or 0
    if existing:
        return 0

    admin = db.scalar(select(User).where(User.username == "admin"))
    if admin is None:
        return 0

    users = {row.username: row for row in db.scalars(select(User)).all()}
    created = 0

    for index, item in enumerate(DEMO_DEMANDS):
        owner = users.get(item["username"]) or admin
        dept = get_or_create_department(db, item["department"])
        demand = Demand(
            user_id=owner.id,
            department_id=dept.id,
            title=item["title"],
            description=item["description"],
            priority=item["priority"],
            status=item["status"],
            creator=owner.username,
            ai_analysis=SAMPLE_AI_ANALYSIS if index % 3 == 0 else None,
        )
        db.add(demand)
        db.flush()
        record_status_change(
            db,
            demand,
            from_status=None,
            to_status=item["status"],
            operator=owner,
            remark="提交 AI 需求",
        )
        created += 1

    db.commit()
    return created


def seed_demo_demands(db: Session, *, replace: bool = False) -> int:
    """写入演示数据；replace=True 时先清空现有需求。"""
    from sqlalchemy import delete

    if replace:
        db.execute(delete(Demand))
        db.commit()
        return seed_demo_demands_if_empty(db)

    return seed_demo_demands_if_empty(db)
