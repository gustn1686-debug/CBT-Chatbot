# Synap (CBT Chatbot PWA)

CBT 기반 챗봇 PWA 프로젝트.

## 구조

```
synap/
├── frontend/   # React + TypeScript + Vite + Tailwind PWA (현수)
├── backend/    # FastAPI (지예)
├── model/
│   ├── finetune/   # 파인튜닝 (현수)
│   ├── harness/    # 하네스 프롬프트 (지예)
│   ├── eval/       # 모델 비교 평가 (공동)
│   └── serving/    # 모델 서버 실행 스크립트 (현수)
├── docs/       # API 명세, 기획 문서
└── README.md
```

## 기술 스택

| 영역 | 사용 기술 |
|---|---|
| 프론트엔드 (`frontend/`) | TypeScript, React 19, React Router 7, Vite 8, Tailwind CSS 4, PWA(`vite-plugin-pwa`) |
| 프론트 테스트·린트 | Vitest, Testing Library, jsdom, oxlint |
| 백엔드 (`backend/`) | Python, FastAPI, Uvicorn, pydantic-settings |
| 데이터베이스 | SQLAlchemy 2.0 + Alembic. 로컬은 SQLite, 배포는 Supabase(Postgres, `psycopg`) |
| 인증 | 직접 구현한 JWT(PyJWT), 비밀번호 해시는 표준 라이브러리 `scrypt` (Supabase Auth는 쓰지 않음) |
| 실시간 응답 | SSE(Server-Sent Events) 스트리밍 |
| 모델 호출 | OpenAI 호환 `/chat/completions` 스트리밍(`httpx`). 모델 서버가 없을 때는 `LLM_MODE=mock` |
| 백엔드 테스트·린트 | pytest, ruff |
| 모델 학습 (`model/`) | PyTorch, Transformers, TRL, PEFT(QLoRA), bitsandbytes, Accelerate. 현재 연구는 Qwen3.5-27B DPO |
| 모델 비교 실험 | llama.cpp(GGUF 양자화)로 후보 모델(Qwen, Gemma, Mistral, EXAONE, Llama) 비교 |
| 모델 평가 | CTRS 6개 항목 LLM-as-a-judge 파이프라인(`model/eval/ctrs_judge`) |
| 디자인 | Figma(상담챗봇_와이어프레임) |
| 협업 | GitHub(브랜치 → PR → 리뷰), CodeRabbit 자동 리뷰 |

### 아직 정해지지 않았거나 준비 중인 것
- **서비스용 모델 서버**: 실행 방식과 주소가 아직 없다 (`model/serving/`이 비어 있고 `model_release.json`의 `inference_endpoint_url`도 `null`). 정해지면 백엔드의 `LLM_MODE=http`, `LLM_BASE_URL`, `LLM_MODEL`만 채우면 연결된다.
- **배포**: 프론트는 Vercel, DB는 Supabase를 쓸 계획이지만 배포 설정 파일(`vercel.json` 등)은 아직 없다. 백엔드를 어디에 올릴지도 미정.
- **CI**: `.github/workflows`가 없어서 PR에서 자동으로 테스트가 돌지 않는다. (지금은 로컬에서 `pytest`, `npm test`를 실행)
- **프론트 의존성**: `zustand`(상태 관리)와 `msw`(API 목킹)가 `package.json`에는 있지만 현재 `frontend/src`에서 쓰이지 않는다. 목업은 `src/api/mock*.ts`로 직접 구현했다.

## 시작하기
1. `.env.example`을 복사해 `.env`를 만들고 값을 채움 (`.env`는 커밋 금지)
2. 각 폴더의 README 참고 (추가 예정)

## 협업 규칙
- main에 직접 push 하지 않고, 브랜치 → PR → 리뷰 후 merge
- 브랜치: `feat/`, `fix/`, `docs/`, `model/`, `chore/` + 소문자-하이픈
- 커밋: `종류: 내용` (feat, fix, style, refactor, docs, chore)
- 모델 가중치·데이터셋은 Hugging Face Hub 비공개 저장소에서 관리하고, 위치는 `model/README.md`에 기록

## Qwen3.5-27B DPO 연구

[실험 파이프라인·프롬프트·코드·현재 결과](model/dpo_pipeline/README.md) · [향후 모델 주소 등록](model/dpo_pipeline/docs/MODEL_RELEASE.md)
