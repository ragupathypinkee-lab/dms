from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.api.deps import get_session_user
from app.core.security import verify_password
from app.db.session import get_db
from app.models import User
from app.web.templating import templates

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login_form(request: Request, db: Session = Depends(get_db)):
    if get_session_user(request, db):
        return RedirectResponse(url="/demand/list", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"request": request, "error": None},
    )


@router.post("/login")
async def login(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
) -> Response:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"request": request, "error": "用户名或密码错误"},
            status_code=401,
        )

    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role
    return RedirectResponse(url="/demand/list", status_code=303)


@router.get("/logout")
async def logout(request: Request) -> Response:
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)
