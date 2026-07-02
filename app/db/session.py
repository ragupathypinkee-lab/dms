from collections.abc import Generator

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

DEFAULT_USERS = (
    ("admin", "admin123", "admin"),
    ("user", "user", "user"),
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_users(db: Session) -> None:
    from app.models import User

    for username, password, role in DEFAULT_USERS:
        exists = db.scalar(select(User.id).where(User.username == username))
        if exists is None:
            db.add(
                User(
                    username=username,
                    password_hash=hash_password(password),
                    role=role,
                )
            )
    db.commit()


def migrate_default_passwords(db: Session) -> None:
    """确保默认账号可用（bcrypt 升级或 SECRET_KEY 变更后的兼容）。"""
    from app.core.security import hash_password, needs_password_upgrade, verify_password
    from app.models import User

    changed = False
    for username, password, _role in DEFAULT_USERS:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            continue
        if needs_password_upgrade(user.password_hash) or not verify_password(
            password, user.password_hash
        ):
            user.password_hash = hash_password(password)
            changed = True
    if changed:
        db.commit()


def migrate_demands(db: Session) -> None:
    from app.models import Demand, User

    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("demands")}
    if "user_id" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE demands ADD COLUMN user_id INTEGER"))

    for demand in db.scalars(select(Demand).where(Demand.user_id.is_(None))):
        owner = db.scalar(select(User).where(User.username == demand.creator))
        if owner:
            demand.user_id = owner.id
    db.commit()


def migrate_status_logs(db: Session) -> None:
    from app.services.status_log import backfill_status_logs, dedupe_initial_status_logs

    dedupe_initial_status_logs(db)
    backfill_status_logs(db)


DEFAULT_DEPARTMENTS = (
    "教务处",
    "学生处",
    "科研处",
    "图书馆",
    "招生办",
    "财务处",
    "后勤处",
    "人事处",
)


def seed_departments(db: Session) -> None:
    from app.models import Department

    for index, name in enumerate(DEFAULT_DEPARTMENTS):
        exists = db.scalar(select(Department.id).where(Department.name == name))
        if exists is None:
            db.add(Department(name=name, sort_order=index))
    db.commit()


def migrate_departments(db: Session) -> None:
    from app.models import Demand
    from app.services.department import get_or_create_department

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "departments" not in tables:
        return

    demand_columns = {column["name"] for column in inspector.get_columns("demands")}
    if "department_id" not in demand_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE demands ADD COLUMN department_id INTEGER"))

    if "department" in demand_columns:
        rows = db.execute(
            text("SELECT id, department FROM demands WHERE department_id IS NULL")
        ).all()
        for row in rows:
            dept = get_or_create_department(db, row.department or "未分类")
            db.execute(
                text("UPDATE demands SET department_id = :dept_id WHERE id = :id"),
                {"dept_id": dept.id, "id": row.id},
            )
        db.commit()

        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE demands DROP COLUMN department"))

    orphan = db.scalar(
        select(func.count()).select_from(Demand).where(Demand.department_id.is_(None))
    )
    if orphan:
        default = get_or_create_department(db, "未分类")
        for demand in db.scalars(select(Demand).where(Demand.department_id.is_(None))):
            demand.department_id = default.id
        db.commit()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_users(db)
        migrate_default_passwords(db)
        seed_departments(db)
        migrate_departments(db)
        migrate_demands(db)
        migrate_status_logs(db)
        from app.db.demo_seed import seed_demo_demands_if_empty

        seed_demo_demands_if_empty(db)
