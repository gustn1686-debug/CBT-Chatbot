from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.db import Base


def _config(connection) -> Config:
    cfg = Config("alembic.ini")
    cfg.attributes["connection"] = connection
    return cfg


def test_migrations_match_models(tmp_path):
    """마이그레이션을 끝까지 적용한 결과가 모델 정의와 같아야 한다 (모델만 고치고 마이그레이션을 빼먹는 실수 방지)."""
    engine = create_engine(f"sqlite:///{tmp_path}/mig.db")
    with engine.begin() as conn:
        command.upgrade(_config(conn), "head")

    with engine.connect() as conn:
        assert {"users", "conversations", "messages", "crisis_events"} <= set(
            inspect(conn).get_table_names()
        )
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
        assert diff == [], f"모델과 마이그레이션이 다릅니다: {diff}"


def test_downgrade_to_base(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/mig.db")
    with engine.begin() as conn:
        cfg = _config(conn)
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")
        assert set(inspect(conn).get_table_names()) <= {"alembic_version"}
