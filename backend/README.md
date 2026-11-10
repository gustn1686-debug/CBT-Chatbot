# Backend (FastAPI)

## 처음 세팅
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example ../.env   # 루트에 .env 생성 후 값 채우기
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
