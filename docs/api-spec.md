# Synap API 명세 (초안)

> 상태: **초안** — 현수와 합의 후 확정. `미정` 표시는 합의가 필요한 항목.
> 구현 후에는 FastAPI가 만드는 OpenAPI(`/docs`)가 기준이 되고, 이 문서는 설계 의도를 설명한다.

## 1. 공통

- Base URL: `/api/v1`
- 형식: JSON (`Content-Type: application/json`), 채팅 응답만 SSE
- 시간: ISO 8601 UTC (`2026-10-02T04:33:15Z`)
- ID: 문자열(UUID)

### 인증
- 모든 요청(`/health`, `/auth/*` 제외)에 `Authorization: Bearer <access_token>` 필요
- 토큰은 **비회원(guest)** 과 **회원(user)** 두 종류. 토큰 payload에 `kind: "guest" | "user"` 포함
- 비회원도 대화 가능. 회기가 일정 수 이상이면 가입 안내(`signup_required`)

### 에러 포맷
```json
{ "code": "auth_invalid_token", "message": "토큰이 유효하지 않습니다." }
```

| HTTP | code 예시 | 의미 |
|------|-----------|------|
| 400 | `bad_request` | 요청 형식 오류 |
| 401 | `auth_invalid_token` | 토큰 없음/만료 |
| 403 | `forbidden` | 남의 대화 접근 등 |
| 404 | `not_found` | 리소스 없음 |
| 409 | `email_taken` | 이미 가입된 이메일 |
| 422 | `validation_error` | 필드 검증 실패 |
| 429 | `rate_limited` | 요청 과다 |
| 500 | `internal_error` | 서버 오류 |

### 페이지네이션
- `GET` 목록: `?limit=20&cursor=<opaque>` → `{ "items": [...], "next_cursor": "..." | null }`

---

## 2. Health

### `GET /health`
```json
{ "status": "ok" }
```

---

## 3. 인증

### `POST /auth/guest` — 비회원 토큰 발급
요청 바디 없음.
```json
{ "access_token": "...", "kind": "guest", "expires_in": 2592000 }
```

### `POST /auth/register` — 회원가입
```json
// 요청
{ "email": "a@example.com", "password": "********", "nickname": "지예" }
// 응답 201
{ "access_token": "...", "kind": "user", "user": { "id": "...", "email": "a@example.com", "nickname": "지예" } }
```
- 비회원 토큰으로 호출하면 그 비회원의 대화가 새 계정으로 **이관**된다 (아래 `/auth/upgrade`와 동일 동작; 하나로 합칠지 `미정`)

### `POST /auth/login` — 로그인
```json
// 요청
{ "email": "a@example.com", "password": "********" }
// 응답
{ "access_token": "...", "kind": "user", "user": { ... } }
```

### `POST /auth/upgrade` — 비회원 → 회원 이관
비회원 토큰 + 회원가입 정보. 비회원 때의 대화·기록을 새 계정으로 옮긴다.
```json
// 요청
{ "email": "a@example.com", "password": "********", "nickname": "지예" }
// 응답 201: /auth/register 와 동일
```

### `GET /me` — 내 정보
```json
{
  "kind": "guest",
  "user": null,
  "usage": { "session_count": 2, "guest_session_limit": 3, "signup_required": false }
}
```
- `signup_required`: 비회원이고 `session_count >= guest_session_limit` 이면 `true`
- `guest_session_limit` 기본 3 (서버 설정값, `미정`)

### `DELETE /me` — 탈퇴
계정과 모든 대화·메시지를 **즉시** 삭제한다. 되돌릴 수 없다.
```json
// 회원: 비밀번호 재확인 필요
{ "password": "********" }
```
- 응답 `204 No Content`. 비회원은 바디 없이 삭제할 수 있다.
- 회원이 비밀번호를 생략하거나 틀리면 `403 auth_invalid_credentials`.
- 사용자와 연결되지 않은 위기 감지 통계(`crisis_events`)는 남는다.

---

## 4. 대화 (Conversation = 1회기)

### `POST /conversations` — 새 대화 시작
```json
// 요청 (선택)
{ "title": null }
// 응답 201
{ "id": "...", "title": null, "created_at": "...", "updated_at": "...", "message_count": 0 }
```
- 비회원이 한도를 넘겨 새 대화를 만들 때의 처리(차단 vs 안내만)는 `미정`. 초안: 막지 않고 `signup_required`만 알린다.

### `GET /conversations` — 내 대화 목록
```json
{ "items": [ { "id": "...", "title": "...", "updated_at": "...", "message_count": 12 } ], "next_cursor": null }
```

### `GET /conversations/{id}` — 대화 상세 + 메시지
```json
{
  "id": "...",
  "title": "...",
  "messages": [
    { "id": "...", "role": "user", "content": "요즘 잠이 안 와요", "created_at": "..." },
    { "id": "...", "role": "assistant", "content": "...", "crisis": false, "created_at": "..." }
  ]
}
```
- `role`: `user` | `assistant`

### `DELETE /conversations/{id}` — 대화 삭제
`204 No Content`

---

## 5. 채팅 (SSE 스트리밍)

### `POST /conversations/{id}/messages`
```json
// 요청
{ "content": "요즘 잠이 안 와요" }
```
응답: `Content-Type: text/event-stream`

| event | data | 설명 |
|-------|------|------|
| `meta` | `{ "message_id": "...", "crisis": false, "signup_required": false }` | 스트림 시작 시 1회 |
| `token` | `{ "delta": "그렇" }` | 응답 텍스트 조각 (여러 번) |
| `done` | `{ "message_id": "...", "finish_reason": "stop" }` | 정상 종료 |
| `error` | `{ "code": "...", "message": "..." }` | 스트림 중 오류 |

예시:
```
event: meta
data: {"message_id":"m_1","crisis":false,"signup_required":false}

event: token
data: {"delta":"잠이 "}

event: token
data: {"delta":"안 오시는군요."}

event: done
data: {"message_id":"m_1","finish_reason":"stop"}
```

### 위기 감지
- 사용자 메시지를 **서버에서 키워드 매칭**으로 검사하고, 감지되면 LLM을 호출하지 않는다.
- `meta.crisis = true`, 응답은 고정 안내 문구 + 상담 전화 정보를 `token`으로 내려준다.
- 추가 필드 `meta.crisis_resources`(전화번호 목록)를 줄지 `미정` — 초안:
```
data: {"message_id":"m_2","crisis":true,"signup_required":false,
       "crisis_resources":[{"name":"자살예방 상담전화","tel":"109"}]}
```
- 위기 UI는 피그마 전달 후 확정 (`미정`)

---

## 6. 후속 범위 (명세 추후 확정)

- 감정 체크인: `POST /checkins`, `GET /checkins`
- 생각 기록(인지 왜곡 태깅): `POST /thought-records`, `GET /thought-records`

---

## 7. 합의가 필요한 항목 (`미정` 모음)

1. 가입 유도 기준 회기 수 (`guest_session_limit`, 기본 3)
2. `/auth/register` 와 `/auth/upgrade` 를 하나로 합칠지
3. 한도 초과 시 새 대화 차단 여부 (초안: 차단 안 함, 안내만)
4. `crisis`, `signup_required`, `crisis_resources` 플래그 규격 및 위기 UI
5. 대화 데이터 보관 기간 및 삭제 정책
6. 비회원 토큰 유효기간 (초안: 30일)
