from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Demand, User


def get_session_user(request: Request, db: Session) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_session_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def owns_demand(user: User, demand: Demand) -> bool:
    if demand.user_id is not None:
        return demand.user_id == user.id
    return demand.creator == user.username


def can_manage_demand(user: User, demand: Demand) -> bool:
    return user.role == "admin" or owns_demand(user, demand)


def ensure_can_manage(user: User, demand: Demand) -> None:
    if not can_manage_demand(user, demand):
        raise HTTPException(status_code=403, detail="无权操作该需求")


def require_admin(current_user: User = Depends(require_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")
    return current_user
