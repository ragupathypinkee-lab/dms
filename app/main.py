from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

app.include_router(api_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 403:
        if request.url.path.startswith("/demand"):
            return RedirectResponse(url="/demand/list?msg=forbidden", status_code=303)
        if request.url.path.startswith("/user") and request.url.path != "/user/password":
            return RedirectResponse(url="/demand/list?msg=admin_forbidden", status_code=303)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.middleware("http")
async def login_required_middleware(request: Request, call_next):
    path = request.url.path
    public_prefixes = ("/static", "/auth/", "/docs", "/redoc", "/openapi.json")
    if path == "/health" or path.startswith(public_prefixes):
        return await call_next(request)

    if path.startswith("/demand") or path.startswith("/user") or path == "/":
        if "user_id" not in request.session:
            return RedirectResponse(url="/auth/login", status_code=303)

    return await call_next(request)


app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)


@app.get("/")
async def root(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse(url="/auth/login", status_code=303)
    return RedirectResponse(url="/demand/list", status_code=303)


@app.get("/health")
async def health():
    return {"status": "ok"}
