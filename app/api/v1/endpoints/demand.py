import logging
from math import ceil
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload
from starlette.responses import Response

from app.api.deps import (
    can_manage_demand,
    ensure_can_manage,
    require_user,
    verify_csrf_token,
)
from app.db.session import get_db
from app.models import Demand, Department, User
from app.services.ai import analyze_demand
from app.services.department import list_departments
from app.services.status_log import (
    format_status_change,
    get_status_logs,
    record_status_change,
)
from app.utils.status import (
    STAT_COLLECTING_STATUSES,
    STAT_DEVELOPING_STATUSES,
    STAT_LAUNCHED_STATUSES,
    STATUS_FLOW,
    get_status_label,
    normalize_status,
    validate_status,
)
from app.utils.validation import (
    AI_ANALYSIS_MAX_LENGTH,
    ValidationError,
    validate_creator,
    validate_description,
    validate_optional_priority,
    validate_optional_text,
    validate_priority,
    validate_remark,
    validate_title,
)
from app.web.context import flash_redirect, template_context
from app.web.templating import templates

router = APIRouter(prefix="/demand", tags=["demand"])
logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50
MAX_SEARCH_LENGTH = 100


def _list_url(msg: str | None = None) -> str:
    return flash_redirect("/demand/list", msg)


def _apply_user_scope(stmt, user: User):
    if user.role != "admin":
        return stmt.where(Demand.user_id == user.id)
    return stmt


def _build_demand_stmt(
    user: User,
    department_id: int | None = None,
    priority: str | None = None,
    keyword: str | None = None,
):
    stmt = (
        select(Demand)
        .options(joinedload(Demand.department))
        .order_by(Demand.created_at.desc())
    )
    return _apply_demand_filters(
        stmt,
        user,
        department_id=department_id,
        priority=priority,
        keyword=keyword,
    )


def _count_demands(
    db: Session,
    user: User,
    department_id: int | None = None,
    priority: str | None = None,
    keyword: str | None = None,
) -> int:
    stmt = select(func.count(Demand.id))
    stmt = _apply_demand_filters(
        stmt,
        user,
        department_id=department_id,
        priority=priority,
        keyword=keyword,
    )
    return db.scalar(stmt) or 0


def _filter_demands(
    db: Session,
    user: User,
    department_id: int | None = None,
    priority: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[Demand], int, int]:
    total = _count_demands(
        db,
        user,
        department_id=department_id,
        priority=priority,
        keyword=keyword,
    )
    if total == 0:
        return [], 0, 1

    total_pages = max(1, ceil(total / page_size))
    page = min(max(1, page), total_pages)
    offset = (page - 1) * page_size

    stmt = _build_demand_stmt(
        user,
        department_id=department_id,
        priority=priority,
        keyword=keyword,
    )
    stmt = stmt.offset(offset).limit(page_size)
    return list(db.scalars(stmt).unique().all()), total, page


def _get_demand_or_404(db: Session, demand_id: int) -> Demand:
    demand = db.scalar(
        select(Demand)
        .options(joinedload(Demand.department))
        .where(Demand.id == demand_id)
    )
    if demand is None:
        raise HTTPException(status_code=404, detail="需求不存在")
    return demand


def _parse_department_id(value: str | None) -> int | None:
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed


def _parse_page(value: str | None) -> int:
    try:
        page = int(value or 1)
    except ValueError:
        return 1
    return max(1, page)


def _parse_page_size(value: str | None) -> int:
    try:
        size = int(value or DEFAULT_PAGE_SIZE)
    except ValueError:
        return DEFAULT_PAGE_SIZE
    return min(max(1, size), MAX_PAGE_SIZE)


def _parse_keyword(value: str | None) -> str | None:
    if not value:
        return None
    keyword = value.strip()
    if not keyword:
        return None
    return keyword[:MAX_SEARCH_LENGTH]


def _demand_list_url(
    *,
    keyword: str | None = None,
    department_id: int | None = None,
    priority: str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> str:
    params: dict[str, str] = {}
    if keyword:
        params["q"] = keyword
    if department_id:
        params["department_id"] = str(department_id)
    if priority:
        params["priority"] = priority
    if page > 1:
        params["page"] = str(page)
    if page_size != DEFAULT_PAGE_SIZE:
        params["page_size"] = str(page_size)
    query = urlencode(params)
    return f"/demand/list?{query}" if query else "/demand/list"


def _apply_demand_filters(
    stmt,
    user: User,
    *,
    department_id: int | None = None,
    priority: str | None = None,
    keyword: str | None = None,
):
    stmt = _apply_user_scope(stmt, user)
    if department_id:
        stmt = stmt.where(Demand.department_id == department_id)
    if priority:
        stmt = stmt.where(Demand.priority == priority)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.join(Demand.department).where(
            or_(
                Demand.title.ilike(pattern),
                Demand.description.ilike(pattern),
                Demand.creator.ilike(pattern),
                Department.name.ilike(pattern),
            )
        )
    return stmt


def _parse_demand_fields(
    db: Session,
    current_user: User,
    *,
    title: str,
    description: str,
    department_id: int,
    priority: str,
    creator: str,
    ai_analysis: str | None,
):
    title = validate_title(title)
    description = validate_description(description)
    priority = validate_priority(priority)
    department = db.get(Department, department_id)
    if department is None:
        raise ValidationError("无效的申请单位")
    if current_user.role == "admin":
        creator = validate_creator(creator)
    else:
        creator = current_user.username
    ai_analysis = validate_optional_text(ai_analysis, max_length=AI_ANALYSIS_MAX_LENGTH)
    return title, description, priority, creator, ai_analysis, department


def _get_stats(db: Session, user: User) -> dict[str, int]:
    total_stmt = _apply_user_scope(select(func.count()).select_from(Demand), user)
    evaluating_stmt = _apply_user_scope(
        select(func.count())
        .select_from(Demand)
        .where(Demand.status.in_(STAT_COLLECTING_STATUSES)),
        user,
    )
    developing_stmt = _apply_user_scope(
        select(func.count())
        .select_from(Demand)
        .where(Demand.status.in_(STAT_DEVELOPING_STATUSES)),
        user,
    )
    completed_stmt = _apply_user_scope(
        select(func.count())
        .select_from(Demand)
        .where(Demand.status.in_(STAT_LAUNCHED_STATUSES)),
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
    q: str | None = None,
    department_id: str | None = None,
    priority: str | None = None,
    page: str | None = None,
    page_size: str | None = None,
):
    parsed_department_id = _parse_department_id(department_id)
    parsed_priority = None
    try:
        parsed_priority = validate_optional_priority(priority)
    except ValidationError:
        parsed_priority = None

    keyword = _parse_keyword(q)
    parsed_page = _parse_page(page)
    parsed_page_size = _parse_page_size(page_size)

    demands, total, parsed_page = _filter_demands(
        db,
        current_user,
        department_id=parsed_department_id,
        priority=parsed_priority,
        keyword=keyword,
        page=parsed_page,
        page_size=parsed_page_size,
    )
    total_pages = max(1, ceil(total / parsed_page_size)) if total else 1

    pagination = {
        "page": parsed_page,
        "page_size": parsed_page_size,
        "total": total,
        "total_pages": total_pages,
        "has_prev": parsed_page > 1,
        "has_next": parsed_page < total_pages,
    }
    has_filters = bool(keyword or parsed_department_id or parsed_priority)

    return templates.TemplateResponse(
        request=request,
        name="demand/list.html",
        context=template_context(
            request,
            current_user=current_user,
            active_page="list",
            demands=demands,
            keyword=keyword,
            department_id=parsed_department_id,
            priority=parsed_priority,
            pagination=pagination,
            has_filters=has_filters,
            demand_list_url=_demand_list_url,
            stats=_get_stats(db, current_user),
            departments=list_departments(db),
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
    departments = list_departments(db)
    return templates.TemplateResponse(
        request=request,
        name="demand/form.html",
        context=template_context(
            request,
            current_user=current_user,
            active_page="create",
            demand=None,
            page_title="提交 AI 需求",
            page_subtitle="填写场景与目标，提交后进入智能体孵化流程",
            form_action="/demand/create",
            status_flow=STATUS_FLOW,
            normalize_status=normalize_status,
            get_status_label=get_status_label,
            departments=departments,
        ),
    )


@router.post("/create")
async def create_demand(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    title: str = Form(...),
    description: str = Form(...),
    department_id: int = Form(...),
    priority: str = Form(...),
    creator: str = Form(...),
    ai_analysis: str | None = Form(None),
    _: None = Depends(verify_csrf_token),
) -> Response:
    if not list_departments(db):
        return RedirectResponse(url=_list_url("no_department"), status_code=303)

    try:
        title, description, priority, creator, ai_analysis, department = _parse_demand_fields(
            db,
            current_user,
            title=title,
            description=description,
            department_id=department_id,
            priority=priority,
            creator=creator,
            ai_analysis=ai_analysis,
        )
    except ValidationError:
        return RedirectResponse(
            url=flash_redirect("/demand/create", "validation_error"),
            status_code=303,
        )

    demand_status = "collecting"
    demand = Demand(
        user_id=current_user.id,
        department_id=department.id,
        title=title,
        description=description,
        priority=priority,
        status=demand_status,
        creator=creator,
        ai_analysis=ai_analysis,
    )
    db.add(demand)
    db.flush()
    record_status_change(
        db,
        demand,
        from_status=None,
        to_status=demand_status,
        operator=current_user,
        remark="提交 AI 需求",
    )
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
    status_logs = get_status_logs(db, demand.id)
    return templates.TemplateResponse(
        request=request,
        name="demand/form.html",
        context=template_context(
            request,
            current_user=current_user,
            active_page="list",
            demand=demand,
            page_title="编辑 AI 需求",
            page_subtitle=f"修改需求 #{demand.id}，推进智能体落地",
            form_action=f"/demand/edit/{demand.id}",
            status_flow=STATUS_FLOW,
            normalize_status=normalize_status,
            get_status_label=get_status_label,
            departments=list_departments(db),
            status_logs=status_logs,
            format_status_change=format_status_change,
        ),
    )


@router.post("/edit/{id}")
async def update_demand(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    title: str = Form(...),
    description: str = Form(...),
    department_id: int = Form(...),
    priority: str = Form(...),
    creator: str = Form(...),
    ai_analysis: str | None = Form(None),
    _: None = Depends(verify_csrf_token),
) -> Response:
    demand = _get_demand_or_404(db, id)
    ensure_can_manage(current_user, demand)

    try:
        title, description, priority, creator, ai_analysis, department = _parse_demand_fields(
            db,
            current_user,
            title=title,
            description=description,
            department_id=department_id,
            priority=priority,
            creator=creator,
            ai_analysis=ai_analysis,
        )
    except ValidationError:
        return RedirectResponse(
            url=flash_redirect(f"/demand/edit/{id}", "validation_error"),
            status_code=303,
        )

    demand.title = title
    demand.description = description
    demand.department_id = department.id
    demand.priority = priority
    if current_user.role == "admin":
        demand.creator = creator
    demand.ai_analysis = ai_analysis
    db.commit()
    return RedirectResponse(url=_list_url("updated"), status_code=303)


@router.post("/status/{id}")
async def update_status(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    status: str = Form(...),
    remark: str = Form(""),
    _: None = Depends(verify_csrf_token),
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

    old_status = normalize_status(demand.status)
    if old_status != new_status:
        try:
            remark_text = validate_remark(remark)
        except ValidationError as exc:
            if _wants_json(request):
                return JSONResponse(
                    status_code=400,
                    content={"ok": False, "detail": exc.message},
                )
            if "备注" in exc.message and "不能超过" not in exc.message:
                return RedirectResponse(url=_list_url("status_remark_required"), status_code=303)
            return RedirectResponse(url=_list_url("status_remark_too_long"), status_code=303)

        demand.status = new_status
        record_status_change(
            db,
            demand,
            from_status=old_status,
            to_status=new_status,
            operator=current_user,
            remark=remark_text,
        )
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
    _: None = Depends(verify_csrf_token),
):
    demand = _get_demand_or_404(db, id)
    ensure_can_manage(current_user, demand)

    try:
        analysis = analyze_demand(demand)
    except Exception:
        logger.exception("Unexpected error during AI analysis for demand %s", demand.id)
        if _wants_json(request):
            return JSONResponse(
                status_code=500,
                content={"ok": False, "detail": "AI 评估失败，请稍后重试"},
            )
        return RedirectResponse(
            url=flash_redirect(f"/demand/edit/{id}", "ai_analyze_failed"),
            status_code=303,
        )

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
    _: None = Depends(verify_csrf_token),
) -> Response:
    demand = _get_demand_or_404(db, id)
    ensure_can_manage(current_user, demand)
    db.delete(demand)
    db.commit()
    return RedirectResponse(url=_list_url("deleted"), status_code=303)
