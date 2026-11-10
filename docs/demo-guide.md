# 시연 가이드 (노트북 1대 + RunPod 모델 서버)

시연은 **노트북 한 대**에서 백엔드와 프론트를 같이 띄우고, 모델만 RunPod(A100 80GB)의 vLLM 서버에서 받아온다. 배포(AWS/Vercel/Supabase)는 필요 없다.

```
[노트북]
  브라우저 ── 프론트(5173) ── 백엔드(8000, SQLite) ──(인터넷)──▶ [RunPod] vLLM (OpenAI 호환 API)
```

## 0. 역할

| 누가 | 할 일 |
|---|---|
| 모델팀 | RunPod에서 vLLM으로 모델을 서빙하고 **접속 주소 · API 키 · 모델 이름**을 전달 |
| 백엔드/프론트 | 아래 순서로 노트북에서 실행 |

모델팀에 요청할 것
- vLLM을 OpenAI 호환 서버로 실행 (`--api-key`로 키 설정, `--served-model-name`으로 모델 이름 고정)
- 앞부분 처리를 줄이기 위해 `--enable-prefix-caching` 켜기 (요청마다 시스템 프롬프트·이전 대화 요약이 앞에 붙는다)
- 어떤 정밀도(BF16/FP8/4bit)로 올렸는지 알려주기 (`model/dpo_pipeline/model_release.json`의 `inference_precision`과 맞추기)
- 모델에 thinking 모드가 있다면 대화에서는 끌 수 있는지 확인
- 시연 시간대에는 그 GPU를 학습·평가에 쓰지 않기 (같은 GPU를 쓰면 서로 느려진다)

## 1. 처음 한 번만 (준비)

필요한 것: Python 3, Node.js, 이 저장소 클론.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

```bash
cd frontend
npm install
```

### 환경변수 — 파일이 둘로 나뉜다

백엔드와 프론트는 **서로 다른 `.env` 파일**을 읽는다. (둘 다 git에 올라가지 않는다)

**① 레포 루트 `.env`** — 백엔드가 읽는다. `.env.example`을 복사해서 만든다.

```bash
cp .env.example .env
```

```
JWT_SECRET=<아무 긴 문자열로 변경>
CRISIS_LOG_SECRET=<아무 긴 문자열로 변경>

LLM_MODE=http
LLM_BASE_URL=https://<pod-id>-8000.proxy.runpod.net/v1
LLM_API_KEY=<모델팀이 알려준 키>
LLM_MODEL=<vLLM의 --served-model-name 값>
```

**② `frontend/.env.local`** — 프론트(Vite)가 읽는다. 루트 `.env`의 `VITE_*` 값은 프론트에 **적용되지 않는다**.

```
VITE_USE_MOCK=false
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

`VITE_USE_MOCK=false`를 빼먹으면 화면은 뜨지만 가짜(목업) 응답이 나온다.

### DB 만들기

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

로컬 SQLite 파일(`backend/synap.db`)이 만들어진다.

## 2. 모델 서버부터 확인 (우리 코드와 무관하게)

백엔드를 띄우기 전에, 모델 서버 자체가 되는지 `curl`로 먼저 본다.

```bash
curl -s https://<pod-id>-8000.proxy.runpod.net/v1/models -H "Authorization: Bearer <키>"
```

모델 이름이 보이면 서버가 살아 있는 것이다. 스트리밍 응답까지 보려면:

```bash
curl -N https://<pod-id>-8000.proxy.runpod.net/v1/chat/completions \
  -H "Authorization: Bearer <키>" -H "Content-Type: application/json" \
  -d '{"model":"<모델 이름>","stream":true,"messages":[{"role":"user","content":"요즘 잠이 안 와요"}]}'
```

`data: {...}` 줄이 계속 나오다가 `data: [DONE]`으로 끝나야 한다.

## 3. 실행 (터미널 두 개)

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

```bash
cd frontend
npm run dev
```

브라우저에서 **`http://localhost:5173`** 을 연다.

> 주소는 꼭 `localhost:5173`이어야 한다. `127.0.0.1`이나 `npm run preview`(4173 포트)로 열면 백엔드 CORS(`CORS_ORIGINS`, 기본 `http://localhost:5173`)에 막힌다.

## 4. 시연 전날 리허설 체크리스트

- [ ] RunPod Pod가 켜져 있고 모델 로딩이 끝났다 (2번의 `curl` 통과)
- [ ] 대화에서 응답이 한 글자씩 스트리밍된다
- [ ] 한국어 상담 톤이 나온다 (영어나 이상한 형식이 아니다)
- [ ] 첫 응답까지 걸리는 시간이 허용 범위다
- [ ] 대화 종료 후 요약이 저장된다 (아래 확인 방법)
- [ ] 새 대화에서 이전 대화 내용을 자연스럽게 기억한다
- [ ] 노트북이 인터넷에 안정적으로 연결돼 있다 (화면 잠금·절전 해제)
- [ ] 백업 준비: 녹화 영상 또는 `LLM_MODE=mock` 전환 방법 확인

요약 저장 확인:

```bash
cd backend
sqlite3 synap.db "select title, summary_seq, summary from conversations"
```

`summary`에 JSON(상황, 처음 떠오른 생각, 감정 등)이 들어 있어야 한다. 요약 프롬프트는 mock에서만 확인했고 **실제 모델로는 아직 검증하지 않았다.** 리허설에서 요약이 비어 있거나 형식이 깨지면 `backend/app/services/summary.py`의 프롬프트를 손봐야 한다.

## 5. 시연 흐름 예시

1. 시작 화면에서 "비회원으로 먼저 써볼게요" → 홈
2. "대화 시작하기" → 고민을 이야기하고 응답 확인
3. "뒤로" 또는 "대화 종료" → 홈 "지난 대화" 목록에 대화가 보임
4. 지난 대화를 눌러 이어서 대화
5. "대화 시작하기"로 새 대화 → 이전 대화를 기억하는지 확인
6. (선택) 가입 → 로그아웃 후 로그인, 대화가 이어지는지 확인
7. (선택) 위기 표현 → 상담 전화 안내 시트

> 위기 감지의 키워드·문구·전화번호는 **임시안**이다. 시연 전에 팀에서 확정하자. 위기 표현은 LLM을 부르지 않고 서버의 고정 문구로 응답한다.

## 6. 문제가 생기면

| 증상 | 원인과 해결 |
|---|---|
| 보낸 메시지에 "전송 실패"(다시 시도)가 뜨고 응답이 없음 | 모델 서버에 연결하지 못한 것(SSE `error` 이벤트, 코드 `llm_unavailable`). RunPod Pod가 꺼졌거나 주소/키가 틀림. 2번 `curl`로 확인 |
| 가짜 같은 짧은 응답만 나옴 | `LLM_MODE`가 `mock`이거나 백엔드를 재시작하지 않음. 루트 `.env` 수정 후 백엔드 재시작 |
| 화면은 뜨는데 응답이 항상 정해진 문장(목업) | `frontend/.env.local`의 `VITE_USE_MOCK=false` 누락. 프론트 재시작 |
| 브라우저 콘솔에 CORS 오류 | 주소를 `http://localhost:5173`으로 열었는지 확인 |
| 로그인/대화 API가 500 | `alembic upgrade head`를 했는지 확인. 예전 `synap.db`가 있으면 지우고 다시 `alembic upgrade head` |
| 응답이 너무 느림 | 같은 GPU에서 다른 작업이 도는지 확인. 모델 정밀도·thinking 모드 점검 |
| 자주 "전송 실패"가 뜨는데 모델 서버는 멀쩡함 | 백엔드가 일부러 거절한 것일 수 있다(`llm_busy`/`llm_timeout`). 8번 표의 값을 확인하고 필요하면 `.env`에서 조정 |

모델 서버가 끝내 안 되면 `.env`에서 `LLM_MODE=mock`으로 바꾸고 백엔드를 재시작하면 화면 흐름만이라도 보여줄 수 있다.

## 7. 리허설 후 초기화 / 끝난 뒤

대화 기록을 비우고 처음부터 다시 하려면:

```bash
cd backend
rm synap.db
alembic upgrade head
```

그리고 브라우저에서 사이트 데이터(localStorage)를 지우거나 시크릿 창을 쓴다. (로그인 토큰이 남아 있으면 지워진 계정으로 접속을 시도해 401이 난다.)

시연이 끝나면 **RunPod Pod를 멈춘다.** 켜 둔 시간만큼 비용이 나온다. (멈춤 `stop`과 삭제 `terminate`는 다르다. 삭제하면 접속 주소가 바뀐다.)

## 8. 모델 서버 보호 (동시 호출 제한 · 타임아웃)

백엔드가 모델 서버(GPU)를 보호한다. 기본값은 시연(5~10명)에 맞춰 두었고, 루트 `.env`로 바꿀 수 있다. (`.env.example` 참고)

| 상황 | 동작 | 사용자에게 |
|---|---|---|
| 동시에 응답을 생성하는 요청이 `LLM_MAX_CONCURRENT`(기본 8)개를 넘음 | 최대 `LLM_QUEUE_WAIT_SECONDS`(20초) 기다리게 함 | 평소처럼 응답 |
| 기다리는 줄이 `LLM_MAX_QUEUE`(8)를 넘거나 20초를 기다려도 자리가 안 남 | 바로 거절 (`llm_busy`) | 메시지에 "전송 실패" + 다시 시도 |
| 첫 글자가 `LLM_FIRST_TOKEN_TIMEOUT`(60초) 안에 안 옴 | 중단 (`llm_timeout`) | "전송 실패" + 다시 시도 |
| 글자 사이가 `LLM_IDLE_TIMEOUT`(30초) 넘게 비거나 전체가 `LLM_TOTAL_TIMEOUT`(180초) 초과 | 중단하고, 받은 만큼은 저장 (`llm_timeout`) | 받은 글자까지 보이고 "전송 실패" |
| 회기 요약 | 대화 응답과 **별도로** `LLM_SUMMARY_MAX_CONCURRENT`(1)개씩만 | 보이지 않음 (뒤에서 처리) |

- 요약이 한꺼번에 몰려도 모델에는 한 번에 하나만 가서 대화 응답이 밀리지 않는다.
- 사용자가 화면을 닫아도 점유한 자리는 바로 반납된다.
- 서버가 정말 느리면 `LLM_FIRST_TOKEN_TIMEOUT`을 늘리고, 시연 인원이 적으면 `LLM_MAX_CONCURRENT`를 줄여도 된다. (A100 80GB 한 장 기준의 적정값은 리허설에서 정한다)
- 프론트는 거절·시간 초과를 모두 "전송 실패"로 보여주고 다시 시도할 수 있게 한다. "이용자가 많아요" 같은 구체적인 안내 문구는 아직 화면에 나오지 않는다.

## 9. 알려진 한계 (시연 전에 알아둘 것)

- 동시 호출 제한 값은 **어림값**이다. 실제 모델 서버(RunPod)로 부하 테스트를 해 보고 맞춰야 한다.
- 시스템 프롬프트와 위기 문구는 임시안이다. (`model/harness` 확정 후 교체)
- 비밀번호 재설정, 이메일 인증은 없다.
