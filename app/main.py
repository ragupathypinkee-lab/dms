from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import init_db

PROTECTED_PREFIXES = ("/demand", "/user", "/department")
PUBLIC_PREFIXES = ("/static", "/auth/", "/health")


def _is_browser_html_request(request: Request) -> bool:
    if request.headers.get("x-requested-with") == "fetch":
        return False
    accept = request.headers.get("accept", "")
    return "text/html" in accept or accept.startswith("*/*")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime()
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

app.include_router(api_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        accept = request.headers.get("accept", "")
        if "application/json" in accept or request.headers.get("x-requested-with") == "fetch":
            return JSONResponse(status_code=401, content={"detail": exc.detail})
        return RedirectResponse(url="/auth/login", status_code=303)

    if exc.status_code == 403:
        if exc.detail == "CSRF 验证失败":
            if request.url.path.startswith("/demand"):
                return RedirectResponse(url="/demand/list?msg=csrf_failed", status_code=303)
            if request.url.path.startswith("/user"):
                if request.url.path == "/user/password":
                    return RedirectResponse(url="/user/password?msg=csrf_failed", status_code=303)
                return RedirectResponse(url="/demand/list?msg=admin_forbidden", status_code=303)
            if request.url.path.startswith("/department"):
                return RedirectResponse(url="/department/list?msg=csrf_failed", status_code=303)
        if request.url.path.startswith("/demand"):
            return RedirectResponse(url="/demand/list?msg=forbidden", status_code=303)
        if request.url.path.startswith("/user") and request.url.path != "/user/password":
            return RedirectResponse(url="/demand/list?msg=admin_forbidden", status_code=303)
        if request.url.path.startswith("/department"):
            return RedirectResponse(url="/demand/list?msg=admin_forbidden", status_code=303)

    if exc.status_code == 404 and _is_browser_html_request(request):
        path = request.url.path
        if path.startswith("/demand"):
            return RedirectResponse(url="/demand/list", status_code=303)
        if path.startswith("/department"):
            return RedirectResponse(url="/department/list", status_code=303)
        if path.startswith("/user"):
            return RedirectResponse(url="/user/list", status_code=303)

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "0"
    if not settings.debug:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
    return response


@app.middleware("http")
async def login_required_middleware(request: Request, call_next):
    path = request.url.path
    if path == "/health" or path.startswith(PUBLIC_PREFIXES):
        return await call_next(request)

    if path == "/" or path.startswith(PROTECTED_PREFIXES):
        if "user_id" not in request.session:
            return RedirectResponse(url="/auth/login", status_code=303)

    return await call_next(request)


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    https_only=not settings.debug,
    same_site="lax",
    max_age=60 * 60 * 8,
)


@app.get("/")
async def root(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse(url="/auth/login", status_code=303)
    return RedirectResponse(url="/demand/list", status_code=303)


@app.get("/health")
async def health():
    return {"status": "ok"}
