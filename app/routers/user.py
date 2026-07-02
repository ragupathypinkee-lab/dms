from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.database import get_db
from app.deps import require_admin, require_user
from app.messages import get_flash_message
from app.models import User
from app.security import hash_password, verify_password
from app.templating import templates

router = APIRouter(prefix="/user", tags=["user"])


def _list_url(msg: str | None = None) -> str:
    return f"/user/list?msg={msg}" if msg else "/user/list"


def _template_context(request: Request, **context):
    msg = request.query_params.get("msg")
    return {
        "request": request,
        "flash_message": get_flash_message(msg),
        **context,
    }


def _password_url(msg: str | None = None) -> str:
    return f"/user/password?msg={msg}" if msg else "/user/password"


@router.get("/list")
async def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    users = list(
        db.scalars(select(User).order_by(User.id.asc())).all()
    )
    return templates.TemplateResponse(
        request=request,
        name="user/list.html",
        context=_template_context(
            request,
            current_user=current_user,
            active_page="users",
            users=users,
        ),
    )


@router.get("/create")
async def create_form(
    request: Request,
    current_user: User = Depends(require_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="user/form.html",
        context=_template_context(
            request,
            current_user=current_user,
            active_page="users",
            page_title="添加用户",
            page_subtitle="创建普通用户账号",
            form_action="/user/create",
        ),
    )


@router.post("/create")
async def create_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    username: str = Form(...),
    password: str = Form(...),
) -> Response:
    username = username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if len(username) > 50:
        raise HTTPException(status_code=400, detail="用户名过长")
    if len(password) < 4:
        return RedirectResponse(url=_list_url("user_password_short"), status_code=303)

    exists = db.scalar(select(User.id).where(User.username == username))
    if exists is not None:
        return RedirectResponse(url=_list_url("user_exists"), status_code=303)

    db.add(
        User(
            username=username,
            password_hash=hash_password(password),
            role="user",
        )
    )
    db.commit()
    return RedirectResponse(url=_list_url("user_created"), status_code=303)


@router.get("/password")
async def password_form(
    request: Request,
    current_user: User = Depends(require_user),
):
    return templates.TemplateResponse(
        request=request,
        name="user/password.html",
        context=_template_context(
            request,
            current_user=current_user,
            active_page="password",
        ),
    )


@router.post("/password")
async def change_password(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
) -> Response:
    if not verify_password(current_password, current_user.password_hash):
        return RedirectResponse(url=_password_url("password_wrong"), status_code=303)
    if len(new_password) < 4:
        return RedirectResponse(url=_password_url("user_password_short"), status_code=303)
    if new_password != confirm_password:
        return RedirectResponse(url=_password_url("password_mismatch"), status_code=303)

    user = db.get(User, current_user.id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse(url=_password_url("password_updated"), status_code=303)
