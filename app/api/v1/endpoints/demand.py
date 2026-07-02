from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.api.deps import can_manage_demand, ensure_can_manage, require_user
from app.db.session import get_db
from app.models import Demand, User
from app.services.ai import analyze_demand
from app.utils.messages import get_flash_message
from app.utils.status import (
    STATUS_FLOW,
    get_status_label,
    normalize_status,
    validate_status,
)
from app.web.templating import templates

router = APIRouter(prefix="/demand", tags=["demand"])


def _list_url(msg: str | None = None) -> str:
    return f"/demand/list?msg={msg}" if msg else "/demand/list"


def _template_context(request: Request, **context):
    msg = request.query_params.get("msg")
    return {
        "request": request,
        "flash_message": get_flash_message(msg),
        **context,
    }


def _apply_user_scope(stmt, user: User):
    if user.role != "admin":
        return stmt.where(Demand.user_id == user.id)
    return stmt


def _build_demand_stmt(
    user: User,
    department: str | None = None,
    priority: str | None = None,
):
    stmt = select(Demand).order_by(Demand.created_at.desc())
    stmt = _apply_user_scope(stmt, user)
    if department:
        stmt = stmt.where(Demand.department == department)
    if priority:
        stmt = stmt.where(Demand.priority == priority)
    return stmt


def _filter_demands(
    db: Session,
    user: User,
    department: str | None = None,
    priority: str | None = None,
) -> list[Demand]:
    stmt = _build_demand_stmt(user, department=department, priority=priority)
    return list(db.scalars(stmt).all())


def _get_demand_or_404(db: Session, demand_id: int) -> Demand:
    demand = db.get(Demand, demand_id)
    if demand is None:
        raise HTTPException(status_code=404, detail="Demand not found")
    return demand


def _get_stats(db: Session, user: User) -> dict[str, int]:
    total_stmt = _apply_user_scope(select(func.count()).select_from(Demand), user)
    evaluating_stmt = _apply_user_scope(
        select(func.count())
        .select_from(Demand)
        .where(Demand.status.in_(["evaluating", "pending"])),
        user,
    )
    developing_stmt = _apply_user_scope(
        select(func.count())
        .select_from(Demand)
        .where(Demand.status.in_(["developing", "in_progress"])),
        user,
    )
    completed_stmt = _apply_user_scope(
        select(func.count())
        .select_from(Demand)
        .where(Demand.status.in_(["completed", "done"])),
        user,
    )
    high_priority_stmt = _apply_user_scope(
        select(func.count()).select_from(Demand).where(Demand.priority == "high"),
        user,
    )
    return {
        "total": db.scalar(total_stmt) or 0,
        "evaluating": db.scalar(evaluating_stmt) or 0,
        "developing": db.scalar(developing_stmt) or 0,
        "completed": db.scalar(completed_stmt) or 0,
        "high_priority": db.scalar(high_priority_stmt) or 0,
    }


def _get_departments(db: Session, user: User) -> list[str]:
    stmt = _apply_user_scope(
        select(distinct(Demand.department)).order_by(Demand.department),
        user,
    )
    return list(db.scalars(stmt).all())


def _wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return (
        "application/json" in accept
        or request.headers.get("x-requested-with") == "fetch"
    )


@router.get("/")
async def index():
    return RedirectResponse(url="/demand/list", status_code=303)


@router.get("/list")
async def list_demands(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    department: str | None = None,
    priority: str | None = None,
):
    demands = _filter_demands(db, current_user, department=department, priority=priority)
    return templates.TemplateResponse(
        request=request,
        name="demand/list.html",
        context=_template_context(
            request,
            current_user=current_user,
            active_page="list",
            demands=demands,
            department=department,
            priority=priority,
            stats=_get_stats(db, current_user),
            departments=_get_departments(db, current_user),
            can_manage_demand=can_manage_demand,
            status_flow=STATUS_FLOW,
            get_status_label=get_status_label,
            normalize_status=normalize_status,
        ),
    )


@router.get("/create")
async def create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    return templates.TemplateResponse(
        request=request,
        name="demand/form.html",
        context=_template_context(
            request,
            current_user=current_user,
            active_page="create",
            demand=None,
            page_title="登记需求",
            page_subtitle="填写需求信息，提交后进入需求列表",
            form_action="/demand/create",
            status_flow=STATUS_FLOW,
            normalize_status=normalize_status,
            get_status_label=get_status_label,
            departments=_get_departments(db, current_user),
        ),
    )


@router.post("/create")
async def create_demand(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    title: str = Form(...),
    description: str = Form(...),
    department: str = Form(...),
    priority: str = Form(...),
    status: str = Form("evaluating"),
    creator: str = Form(...),
    ai_analysis: str | None = Form(None),
) -> Response:
    if current_user.role != "admin":
        creator = current_user.username

    try:
        demand_status = validate_status(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效状态") from None

    demand = Demand(
        user_id=current_user.id,
        title=title,
        description=description,
        department=department,
        priority=priority,
        status=demand_status,
        creator=creator if current_user.role == "admin" else current_user.username,
        ai_analysis=ai_analysis or None,
    )
    db.add(demand)
    db.commit()
    return RedirectResponse(url=_list_url("created"), status_code=303)


@router.get("/edit/{id}")
async def edit_form(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    demand = _get_demand_or_404(db, id)
    ensure_can_manage(current_user, demand)
    return templates.TemplateResponse(
        request=request,
        name="demand/form.html",
        context=_template_context(
            request,
            current_user=current_user,
            active_page="list",
            demand=demand,
            page_title="编辑需求",
            page_subtitle=f"修改需求 #{demand.id} 的信息",
            form_action=f"/demand/edit/{demand.id}",
            status_flow=STATUS_FLOW,
            normalize_status=normalize_status,
            get_status_label=get_status_label,
            departments=_get_departments(db, current_user),
        ),
    )


@router.post("/edit/{id}")
async def update_demand(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    title: str = Form(...),
    description: str = Form(...),
    department: str = Form(...),
    priority: str = Form(...),
    status: str = Form(...),
    creator: str = Form(...),
    ai_analysis: str | None = Form(None),
) -> Response:
    demand = _get_demand_or_404(db, id)
    ensure_can_manage(current_user, demand)
    try:
        demand.status = validate_status(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效状态") from None
    demand.title = title
    demand.description = description
    demand.department = department
    demand.priority = priority
    if current_user.role == "admin":
        demand.creator = creator
    demand.ai_analysis = ai_analysis or None
    db.commit()
    return RedirectResponse(url=_list_url("updated"), status_code=303)


@router.post("/status/{id}")
async def update_status(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    status: str = Form(...),
):
    demand = _get_demand_or_404(db, id)
    ensure_can_manage(current_user, demand)
    try:
        new_status = validate_status(status)
    except ValueError:
        if _wants_json(request):
            return JSONResponse(
                status_code=400, content={"ok": False, "detail": "无效状态"}
            )
        return RedirectResponse(url=_list_url("invalid_status"), status_code=303)

    demand.status = new_status
    db.commit()

    if _wants_json(request):
        return JSONResponse(
            content={
                "ok": True,
                "status": new_status,
                "label": get_status_label(new_status),
                "message": "状态更新成功",
            }
        )
    return RedirectResponse(url=_list_url("status_updated"), status_code=303)


@router.post("/analyze/{id}")
async def analyze_demand_route(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    demand = _get_demand_or_404(db, id)
    ensure_can_manage(current_user, demand)

    try:
        analysis = analyze_demand(demand)
    except Exception as exc:
        if _wants_json(request):
            return JSONResponse(
                status_code=500,
                content={"ok": False, "detail": f"AI 分析失败：{exc}"},
            )
        raise HTTPException(status_code=500, detail="AI 分析失败") from exc

    demand.ai_analysis = analysis.text
    db.commit()

    if _wants_json(request):
        return JSONResponse(
            content={
                "ok": True,
                "ai_analysis": analysis.text,
                "message": analysis.message,
                "is_mock": analysis.is_mock,
            }
        )
    return RedirectResponse(url=f"/demand/edit/{id}?msg=ai_analyzed", status_code=303)


@router.post("/delete/{id}")
async def delete_demand(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> Response:
    demand = _get_demand_or_404(db, id)
    ensure_can_manage(current_user, demand)
    db.delete(demand)
    db.commit()
    return RedirectResponse(url=_list_url("deleted"), status_code=303)
