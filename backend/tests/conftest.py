import os
import tempfile

# app 을 import 하기 전에 테스트용 DB 로 지정
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

import pytest
from fastapi.testclient import TestClient

from app import models  # noqa: F401  (테이블 등록)
from app.db import Base, engine
from app.main import app

# 스키마는 앱이 만들지 않는다(Alembic). 테스트는 모델로 직접 만들고,
# 마이그레이션과 모델이 어긋나지 않는지는 test_migrations.py 가 따로 확인한다.
Base.metadata.create_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
