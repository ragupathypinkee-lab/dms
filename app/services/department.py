from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Department, Demand


def list_departments(db: Session) -> list[Department]:
    stmt = select(Department).order_by(Department.sort_order.asc(), Department.name.asc())
    return list(db.scalars(stmt).all())


def get_department_or_404(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="部门不存在")
    return department


def get_or_create_department(db: Session, name: str) -> Department:
    name = name.strip()
    department = db.scalar(select(Department).where(Department.name == name))
    if department is not None:
        return department
    department = Department(name=name)
    db.add(department)
    db.flush()
    return department


def validate_department_id(db: Session, department_id: int) -> Department:
    try:
        parsed_id = int(department_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="无效部门") from exc
    return get_department_or_404(db, parsed_id)


def count_demands_by_department(db: Session, department_id: int) -> int:
    stmt = select(func.count()).select_from(Demand).where(Demand.department_id == department_id)
    return db.scalar(stmt) or 0
