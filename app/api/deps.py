from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.csrf import validate_csrf
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
        request.session.clear()
        raise HTTPException(status_code=401, detail="请先登录")
    return user


async def verify_csrf_token(request: Request) -> None:
    token = request.headers.get("X-CSRF-Token")
    if not token:
        content_type = request.headers.get("content-type", "")
        if (
            "application/x-www-form-urlencoded" in content_type
            or "multipart/form-data" in content_type
        ):
            form = await request.form()
            token = form.get("csrf_token")
    if isinstance(token, str):
        validate_csrf(request, token)
        return
    validate_csrf(request, None)


def owns_demand(user: User, demand: Demand) -> bool:
    return demand.user_id == user.id


def can_manage_demand(user: User, demand: Demand) -> bool:
    if user.role == "admin":
        return True
    if demand.user_id is None:
        return False
    return owns_demand(user, demand)


def ensure_can_manage(user: User, demand: Demand) -> None:
    if not can_manage_demand(user, demand):
        raise HTTPException(status_code=403, detail="无权操作该需求")


def require_admin(current_user: User = Depends(require_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")
    return current_user
