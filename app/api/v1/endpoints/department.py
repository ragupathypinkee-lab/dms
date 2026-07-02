from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.api.deps import require_admin, verify_csrf_token
from app.db.session import get_db
from app.models import Department, User
from app.services.department import (
    count_demands_by_department,
    get_department_or_404,
    list_departments,
)
from app.utils.validation import ValidationError, validate_department_name, validate_sort_order
from app.web.context import flash_redirect, template_context
from app.web.templating import templates

router = APIRouter(prefix="/department", tags=["department"])


def _list_url(msg: str | None = None) -> str:
    return flash_redirect("/department/list", msg)


@router.get("/list")
async def list_department_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    departments = list_departments(db)
    demand_counts = {
        dept.id: count_demands_by_department(db, dept.id) for dept in departments
    }
    return templates.TemplateResponse(
        request=request,
        name="department/list.html",
        context=template_context(
            request,
            current_user=current_user,
            active_page="departments",
            departments=departments,
            demand_counts=demand_counts,
        ),
    )


@router.get("/create")
async def create_form(
    request: Request,
    current_user: User = Depends(require_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="department/form.html",
        context=template_context(
            request,
            current_user=current_user,
            active_page="departments",
            department=None,
            page_title="添加单位",
            page_subtitle="新增可供各单位选择的校内单位",
            form_action="/department/create",
        ),
    )


@router.post("/create")
async def create_department(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    name: str = Form(...),
    sort_order: int = Form(0),
    _: None = Depends(verify_csrf_token),
) -> Response:
    try:
        name = validate_department_name(name)
        sort_order = validate_sort_order(sort_order)
    except ValidationError:
        return RedirectResponse(
            url=flash_redirect("/department/create", "validation_error"),
            status_code=303,
        )

    exists = db.scalar(select(Department.id).where(Department.name == name))
    if exists is not None:
        return RedirectResponse(url=_list_url("department_exists"), status_code=303)

    db.add(Department(name=name, sort_order=sort_order))
    db.commit()
    return RedirectResponse(url=_list_url("department_created"), status_code=303)


@router.get("/edit/{id}")
async def edit_form(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    department = get_department_or_404(db, id)
    return templates.TemplateResponse(
        request=request,
        name="department/form.html",
        context=template_context(
            request,
            current_user=current_user,
            active_page="departments",
            department=department,
            page_title="编辑单位",
            page_subtitle=f"修改单位「{department.name}」",
            form_action=f"/department/edit/{department.id}",
        ),
    )


@router.post("/edit/{id}")
async def update_department(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    name: str = Form(...),
    sort_order: int = Form(0),
    _: None = Depends(verify_csrf_token),
) -> Response:
    department = get_department_or_404(db, id)
    try:
        name = validate_department_name(name)
        sort_order = validate_sort_order(sort_order)
    except ValidationError:
        return RedirectResponse(
            url=flash_redirect(f"/department/edit/{id}", "validation_error"),
            status_code=303,
        )

    exists = db.scalar(
        select(Department.id).where(Department.name == name, Department.id != id)
    )
    if exists is not None:
        return RedirectResponse(url=_list_url("department_exists"), status_code=303)

    department.name = name
    department.sort_order = sort_order
    db.commit()
    return RedirectResponse(url=_list_url("department_updated"), status_code=303)


@router.post("/delete/{id}")
async def delete_department(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    _: None = Depends(verify_csrf_token),
) -> Response:
    department = get_department_or_404(db, id)
    if count_demands_by_department(db, id) > 0:
        return RedirectResponse(url=_list_url("department_in_use"), status_code=303)

    db.delete(department)
    db.commit()
    return RedirectResponse(url=_list_url("department_deleted"), status_code=303)
