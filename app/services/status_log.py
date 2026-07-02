from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Demand, DemandStatusLog, User
from app.utils.status import get_status_label, normalize_status


def record_status_change(
    db: Session,
    demand: Demand,
    from_status: str | None,
    to_status: str,
    operator: User,
    remark: str | None = None,
) -> DemandStatusLog:
    log = DemandStatusLog(
        demand_id=demand.id,
        from_status=normalize_status(from_status) if from_status else None,
        to_status=normalize_status(to_status),
        operator_id=operator.id,
        operator_name=operator.username,
        remark=remark,
    )
    db.add(log)
    return log


def get_status_logs(db: Session, demand_id: int) -> list[DemandStatusLog]:
    stmt = (
        select(DemandStatusLog)
        .where(DemandStatusLog.demand_id == demand_id)
        .order_by(DemandStatusLog.created_at.asc(), DemandStatusLog.id.asc())
    )
    return list(db.scalars(stmt).all())


def format_status_change(log: DemandStatusLog) -> str:
    to_label = get_status_label(log.to_status)
    if log.from_status is None:
        return f"提交 AI 需求，初始状态：{to_label}"
    from_label = get_status_label(log.from_status)
    return f"{from_label} → {to_label}"


def backfill_status_logs(db: Session) -> int:
    from app.models import Demand

    created = 0
    for demand in db.scalars(select(Demand)):
        exists = db.scalar(
            select(DemandStatusLog.id)
            .where(DemandStatusLog.demand_id == demand.id)
            .limit(1)
        )
        if exists is not None:
            continue
        operator = _resolve_operator(db, demand)
        if operator:
            record_status_change(
                db,
                demand,
                from_status=None,
                to_status=demand.status,
                operator=operator,
                remark="历史数据初始化",
            )
        else:
            db.add(
                DemandStatusLog(
                    demand_id=demand.id,
                    from_status=None,
                    to_status=normalize_status(demand.status),
                    operator_id=None,
                    operator_name=demand.creator,
                    remark="历史数据初始化",
                )
            )
        created += 1
    if created:
        db.commit()
    return created


def _resolve_operator(db: Session, demand: Demand) -> User:
    if demand.user_id:
        user = db.get(User, demand.user_id)
        if user:
            return user
    user = db.scalar(select(User).where(User.username == demand.creator))
    if user:
        return user
    admin = db.scalar(select(User).where(User.username == "admin"))
    if admin:
        return admin
    return db.scalars(select(User).limit(1)).first()
