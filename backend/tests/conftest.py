import os
import tempfile

# app 을 import 하기 전에 테스트용 DB 로 지정
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:  # lifespan(테이블 생성) 실행
        yield c
