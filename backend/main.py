from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import customer, owner, public
from .auth import router as auth_router
from .config import get_settings
from .errors import register_error_handlers

API_PREFIX = "/api/v1"

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_auth()
    yield


app = FastAPI(
    title="Kofein API",
    version="1.0.0",
    description="API агрегатора независимых кофеен. Контракт: docs/api.md.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
register_error_handlers(app)

api = APIRouter(prefix=API_PREFIX)
api.include_router(auth_router)
api.include_router(public.router)
api.include_router(customer.router)
api.include_router(owner.router)
app.include_router(api)

app.mount(
    "/mini-app",
    StaticFiles(directory=Path(__file__).parent / "static", html=True),
    name="mini-app",
)


@app.get("/health", tags=["Служебное"])
async def health_check():
    return {"status": "ok"}
