from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.api.deps import get_session_user, verify_csrf_token
from app.core.config import settings
from app.core.csrf import rotate_csrf_token
from app.core.rate_limit import check_rate_limit, reset_rate_limit
from app.core.security import hash_password, needs_password_upgrade, verify_password
from app.db.session import get_db
from app.models import User
from app.utils.validation import ValidationError, validate_login_password, validate_username
from app.web.context import template_context
from app.web.templating import templates

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.get("/login")
async def login_form(request: Request, db: Session = Depends(get_db)):
    if get_session_user(request, db):
        return RedirectResponse(url="/demand/list", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context=template_context(request, error=None, show_demo_hint=settings.debug),
    )


@router.post("/login")
async def login(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
    _: None = Depends(verify_csrf_token),
) -> Response:
    client_key = _client_key(request)
    if not check_rate_limit(f"login:{client_key}"):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context=template_context(
                request,
                error="登录尝试过于频繁，请 5 分钟后再试",
                show_demo_hint=settings.debug,
            ),
            status_code=429,
        )

    try:
        username = validate_username(username)
        validate_login_password(password)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context=template_context(request, error=exc.message, show_demo_hint=settings.debug),
            status_code=400,
        )

    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context=template_context(
                request,
                error="用户名或密码错误",
                show_demo_hint=settings.debug,
            ),
            status_code=401,
        )

    reset_rate_limit(f"login:{client_key}")
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role
    rotate_csrf_token(request)

    if needs_password_upgrade(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()

    return RedirectResponse(url="/demand/list", status_code=303)


@router.post("/logout")
async def logout(
    request: Request,
    _: None = Depends(verify_csrf_token),
) -> Response:
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)
