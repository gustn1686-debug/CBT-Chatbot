from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (테이블 등록)
from app.api.v1 import auth, health, me
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.db import Base, engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 초기 개발용: 테이블 자동 생성. 스키마가 안정되면 Alembic 마이그레이션으로 교체.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Synap API", version="0.1.0", lifespan=lifespan)
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
