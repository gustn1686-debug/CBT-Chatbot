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
React, TypeScript, Vite, Tailwind CSS / FastAPI / SQLite(로컬)·Supabase Postgres(배포) / Vercel

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
