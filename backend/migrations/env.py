"""Alembic 환경. DB 주소와 모델은 앱 설정(DATABASE_URL, app.models)을 그대로 쓴다."""

from alembic import context

from app import models  # noqa: F401  (테이블 등록)
from app.db import Base, engine

config = context.config
target_metadata = Base.metadata


def _opts() -> dict:
    return {
        "target_metadata": target_metadata,
        "compare_type": True,
        # SQLite 는 ALTER 가 제한적이라 배치 모드로 처리한다
        "render_as_batch": engine.dialect.name == "sqlite",
    }


def run_migrations_offline() -> None:
    context.configure(
        url=engine.url.render_as_string(hide_password=False),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_opts(),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # 테스트 등에서 연결을 직접 넘겨줄 수 있다 (config.attributes["connection"])
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(connection=connection, **_opts())
        with context.begin_transaction():
            context.run_migrations()
        return
    with engine.connect() as connection:
        context.configure(connection=connection, **_opts())
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
