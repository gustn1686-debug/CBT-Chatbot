# Backend (FastAPI)

## 처음 세팅
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example ../.env   # 루트에 .env 생성 후 값 채우기
alembic upgrade head          # DB 테이블 생성 (앱은 테이블을 만들지 않는다)
```

## 실행
```bash
uvicorn app.main:app --reload
```
- http://localhost:8000/docs (Swagger)
- http://localhost:8000/api/v1/health

## 테스트 / 린트
```bash
pytest
ruff check .
```

## 구조
```
app/
├── main.py        # FastAPI 앱, CORS, 라우터 등록
├── db.py          # SQLAlchemy 엔진/세션 (SQLite ↔ Postgres는 DATABASE_URL로 전환)
├── core/config.py # .env 설정
└── api/v1/        # 엔드포인트 (docs/api-spec.md 기준)
```

## 보관 기간 정리 (하루 1회 실행)
```bash
cd backend && python -m app.services.retention
```
비회원(마지막 활동 후 `GUEST_RETENTION_DAYS`), 회원 대화(`MEMBER_RETENTION_DAYS`), 위기 기록(`CRISIS_RETENTION_DAYS`) 중 기간이 지난 데이터를 지운다. 기준은 `docs/db-schema.md` §5.

## DB 마이그레이션 (Alembic)
모델(`app/models.py`)을 바꾸면 마이그레이션을 만들어 같이 커밋한다. 모델과 마이그레이션이 어긋나면 `tests/test_migrations.py` 가 실패한다.
```bash
alembic revision --autogenerate -m "설명"   # 변경분 생성 후 내용 확인
alembic upgrade head                        # 적용
alembic downgrade -1                        # 한 단계 되돌리기
```
- 로컬은 SQLite, 배포는 Supabase(`DATABASE_URL`)로 같은 마이그레이션을 쓴다.
- 새 컬럼이 NOT NULL 이면 기존 행을 위해 `server_default` 를 주거나 데이터 이전 단계를 넣는다.
