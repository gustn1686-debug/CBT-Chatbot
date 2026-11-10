from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, conversations, health, me
from app.core.config import get_settings
from app.core.errors import register_error_handlers

settings = get_settings()


app = FastAPI(title="Synap API", version="0.1.0")
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
