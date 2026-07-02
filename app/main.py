from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import init_db
from app.routers import auth, demand


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

templates = Jinja2Templates(directory=settings.templates_dir)

app.include_router(auth.router)
app.include_router(demand.router)


@app.get("/")
async def root():
    return {"message": settings.app_name}


@app.get("/health")
async def health():
    return {"status": "ok"}
