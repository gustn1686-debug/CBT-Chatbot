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

### `DELETE /conversations` — 내 대화 전체 삭제
설정의 "전체 기록 삭제". `204 No Content`. 회기 요약은 대화와 같은 행이라 함께 지워진다.

### `POST /conversations/{id}/end` — 대화 종료
`204 No Content`. 서버가 이 대화를 **요약해 내부에 저장**한다 (응답은 요약이 끝나기를 기다리지 않는다). 프론트는 별도의 "대화 종료" 버튼 없이, 메시지를 보낸 대화 화면을 떠날 때(다른 대화로 이동, "새 대화", 설정 이동 등) 이 API를 부른다.
- 요약은 사용자에게 노출하지 않는다. `GET /conversations*` 응답에도 포함되지 않는다.
- 종료 없이 나간 대화는, 다음에 `POST /conversations`로 새 대화를 시작할 때 서버가 뒤에서 따라잡아 요약한다.
- 종료한 대화도 `POST /conversations/{id}/messages`로 이어서 할 수 있다. 이어가면 요약은 낡은 것이 되어 다음 기회에 다시 만든다.

### 회기 요약과 "기억"
- 새 대화에서 메시지를 보낼 때, 서버는 사용자의 **이전 대화 요약(최근 3개, 현재 대화 제외)** 을 모델의 시스템 프롬프트에 붙인다. 위기 감지 시에는 LLM을 부르지 않으므로 붙이지 않는다.
- 요약 항목: 상황, 처음 떠오른 생각, 감정, 대화에서 확인한 점, 대안적 생각, 다음 행동 (`conversations.summary` JSON).
- 왼쪽 메뉴의 "지난 대화" 목록은 `GET /conversations`를 그대로 쓰고, 누르면 그 대화를 이어서 한다 (`GET /conversations/{id}` 후 `POST .../messages`).

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

## 6. 상담 계획 (회원만)

몇 회기를 어떤 요일·시각에 할지 정하면, 그 시각에 웹 푸시로 알린다. 대화에서 "상담 마치기"를 누를 때마다 한 회기가 채워지고(도장), 회기 요약을 만든다. 마지막 회기를 마치면 회기 요약을 모아 전체 요약을 만든다. 요약은 모델 API의 `session_summary` / `plan_summary` 모드를 쓴다 (`model/README.md`).

비회원이 부르면 `403 member_required`. 진행 중인 계획은 한 번에 하나다.

공통 응답 `plan`:

```json
{
  "id": "…", "status": "active",            // active | completed (그만둔 계획은 보이지 않는다)
  "total_sessions": 5, "completed_sessions": 2,
  "weekdays": [0, 3], "time": "22:00", "timezone": "Asia/Seoul",   // 0=월 … 6=일
  "schedule_label": "매주 월·목 22:00",
  "next_reminder_at": "2026-11-26T13:00:00Z",   // 진행 중이 아니면 null
  "created_at": "…", "completed_at": null,
  "sessions": [ {"number": 1, "total": 5, "conversation_id": "…", "title": "…",
                 "completed_at": "…", "summary_status": "done", "summary": "줄바꿈이 있는 요약 글"} ],
  "summary_status": null, "summary": null    // 전체 요약. 모든 회기를 마친 뒤에 생긴다
}
```

`summary_status`: `pending`(만드는 중) · `done` · `failed`. 10분 넘게 `pending`이면(서버 재시작 등) `failed`로 보여 다시 시도할 수 있다. 앱은 `pending`인 동안 3초마다 다시 불러온다.

| 요청 | 설명 |
|---|---|
| `GET /plans/current` | `{"plan": …}` 진행 중인 계획. 없으면 가장 최근에 마친 계획, 그것도 없으면 `null` |
| `POST /plans` | `{"total_sessions": 1~12, "weekdays": [...], "time": "HH:MM", "timezone": "Asia/Seoul"}` → 201. 진행 중인 계획이 있으면 `409 plan_exists` |
| `PATCH /plans/{id}` | 일정만 바꾼다 (`weekdays`, `time`, `timezone`). 진행 중일 때만 |
| `POST /plans/{id}/cancel` | 계획 그만두기. 알림이 멈추고, 마친 회기의 대화·요약은 남는다 |
| `POST /plans/{id}/summary/retry` | 실패한 회기 요약 → 전체 요약 순서로 다시 만든다 |
| `POST /conversations/{id}/complete` | **상담 마치기.** 이 대화를 다음 회기로 채운다 → `{"session": …, "plan": …}`. 두 번 눌러도 같은 결과. 사용자 메시지가 없으면 `409 empty_session`, 진행 중인 계획이 없으면 `409 no_active_plan` |
| `GET /conversations/{id}/session` | 마친 회기의 요약 화면 → `{"session": …, "plan": …}` |
| `POST /conversations/{id}/session/summary/retry` | 실패한 회기 요약 다시 만들기 |

- 마친 대화(`GET /conversations/{id}`의 `session`이 있음)에는 더 보낼 수 없다 → `409 session_completed`. 앱은 입력칸 대신 "요약 보기 / 새 대화"를 보여준다.
- 알림만 받고 대화하지 않은 날은 회기에 들어가지 않는다. 그날 이미 회기를 마쳤으면 그날 알림은 보내지 않는다.
- 회기 요약(`session_summary`, 사용자에게 보여줌)은 다음 대화의 기억용 요약(`summary`, §4)과 따로 저장한다. 상담 마치기를 누르면 둘 다 만든다.

## 7. 웹 푸시 (상담 시간 알림)

| 요청 | 설명 |
|---|---|
| `GET /push/public-key` | `{"public_key": "…"}` 브라우저 구독용 공개키. 서버에 VAPID 키가 없으면 `null` (알림 꺼짐). 인증 불필요 |
| `POST /push/subscriptions` | 회원. `{"endpoint": "https://…", "keys": {"p256dh": "…", "auth": "…"}}` (`PushSubscription.toJSON()`) → 204. 같은 기기를 다른 계정이 등록하면 그 계정으로 옮긴다 |
| `DELETE /push/subscriptions` | 회원. `{"endpoint": "…"}` → 204 |
| `POST /push/test` | 회원. 내 기기로 테스트 알림 → `{"sent": 기기 수}`. 키가 없으면 `503 push_disabled` |

알림 내용: `{"title", "body", "url", "tag"}` (JSON). 서비스 워커(`frontend/public/push-sw.js`)가 보여주고, 누르면 `url`(새 대화 `/`)로 연다. 서버는 30초마다 예약 시각이 된 계획을 확인해 보내며, 예약 시각에서 15분이 지나도록 못 보냈으면 그 회차는 건너뛴다. 같은 예약은 한 번만 보낸다 (`last_reminded_slot`). 브라우저가 버린 구독(404/410)은 지운다.

## 8. 후속 범위 (명세 추후 확정)

- 감정 체크인: `POST /checkins`, `GET /checkins`
- ~~생각 기록(`/thought-records`)~~: 기록 목록·상세 화면을 두지 않기로 했다. 같은 용도의 회기 요약은 위 "회기 요약과 기억"처럼 서버 내부에만 저장한다.

---

## 9. 합의가 필요한 항목 (`미정` 모음)

1. 가입 유도 기준 회기 수 (`guest_session_limit`, 기본 3)
2. `/auth/register` 와 `/auth/upgrade` 를 하나로 합칠지
3. 한도 초과 시 새 대화 차단 여부 (초안: 차단 안 함, 안내만)
4. `crisis`, `signup_required`, `crisis_resources` 플래그 규격 및 위기 UI
5. 대화 데이터 보관 기간 및 삭제 정책
6. 비회원 토큰 유효기간 (초안: 30일)
