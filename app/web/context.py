from fastapi import Request

from app.core.csrf import get_or_create_csrf_token
from app.core.config import settings
from app.utils.messages import get_flash_message


def flash_redirect(path: str, msg: str | None = None) -> str:
    return f"{path}?msg={msg}" if msg else path


def template_context(request: Request, **context):
    msg = request.query_params.get("msg")
    return {
        "request": request,
        "flash_message": get_flash_message(msg),
        "csrf_token": get_or_create_csrf_token(request),
        "debug": settings.debug,
        **context,
    }
