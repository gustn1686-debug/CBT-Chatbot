from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, conversations, health, me, plans, push
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.services import push as push_service

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # 상담 시간 알림 예약 확인 (VAPID 키가 있을 때만)
    task = push_service.start_reminders()
    yield
    await push_service.stop_reminders(task)


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
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(plans.router, prefix="/api/v1")
app.include_router(push.router, prefix="/api/v1")
