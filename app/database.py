from collections.abc import Generator

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings
from app.security import hash_password

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


DEFAULT_USERS = (
    ("admin", "admin", "admin"),
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


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_users(db)
        migrate_demands(db)
