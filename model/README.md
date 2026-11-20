# 상담 회기 API와 앱 연동

2026-11-20에 기존 RunPod 엔드포인트에서 상담, 회기별 요약, 5회기 전체 요약을 합성 데이터로 호출해 세 작업의 완료를 확인했습니다. 기존 주소와 키를 그대로 사용합니다.

| 앱에서 일어나는 일 | 백엔드가 보낼 `input.mode` | 모델 | 저장할 값 |
|---|---|---|---|
| 사용자가 메시지를 보냄 | 생략 또는 `chat` | DPO LoRA 적용 | `output.reply`를 상담자 발화로 저장 |
| 대화가 있는 회기를 종료함 | `session_summary` | 베이스 모델 | `output.summary`를 해당 회기에 저장 |
| 같은 계획의 1~5회기 요약이 모두 준비됨 | `plan_summary` | 베이스 모델 | `output.summary`를 해당 계획에 저장 |

모드에 맞춰 워커가 LoRA를 설정합니다. 앱은 자체 백엔드만 호출하고, RunPod 키는 백엔드에 보관합니다.

## 호출 방법

백엔드 서버의 비밀 환경변수 `RUNPOD_API_KEY`에 별도로 전달받은 호출용 키를 등록합니다.

### 1. 상담 메시지 보내기

```bash
API=https://api.runpod.ai/v2/85s1n34ws03tyv
curl -sS -X POST "$API/run" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input":{"messages":[{"role":"user","content":"내일 발표가 걱정돼요."}]}}'
```

### 2. 답변 가져오기

위 응답의 `id`를 `JOB_ID`에 넣고 같은 터미널에서 조회합니다.

```bash
JOB_ID='받은 작업 ID'
curl -sS "$API/status/$JOB_ID" -H "Authorization: Bearer $RUNPOD_API_KEY"
```

`IN_QUEUE` 또는 `IN_PROGRESS`이면 잠시 뒤 같은 ID로 다시 조회합니다. `COMPLETED`이면 위 표에 따라 상담은 `output.reply`, 요약은 `output.summary`를 읽습니다. `FAILED`, `CANCELLED`, `TIMED_OUT`이면 조회를 끝내고 실패로 처리합니다.

### 3. 다음 턴 이어가기

백엔드가 해당 사용자·회기의 이전 발화와 실제 `output.reply`를 저장합니다. 다음 턴에는 그 이력 끝에 새 `user` 발화를 붙여 같은 `/run`으로 보냅니다. 새 회기는 첫 발화부터 시작합니다.

```json
{"input":{"messages":[
  {"role":"user","content":"내일 발표가 걱정돼요."},
  {"role":"assistant","content":"발표에서 어떤 순간이 가장 걱정되시나요?"},
  {"role":"user","content":"첫 문장을 잊어버릴까 봐요."}
]}}
```

### 4. 회기 종료 시 회기별 요약

사용자가 대화를 마치면 해당 회기의 실제 메시지를 순서대로 보냅니다. 첫 역할은 `user`이며 이후에는 `assistant`와 번갈아야 합니다. 마지막 발화는 어느 쪽이든 가능합니다. 아래 JSON을 `request.json`으로 저장합니다.

```json
{
  "input": {
    "mode": "session_summary",
    "messages": [
      {"role": "user", "content": "발표 전에 긴장돼서 첫 문장을 메모했어요."},
      {"role": "assistant", "content": "다음 발표 때도 그 메모를 써 보면 어떨까요?"}
    ]
  }
}
```

```bash
curl --fail-with-body -sS -X POST "$API/run" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" --data-binary @request.json
```

2절과 같이 상태를 조회합니다. 완료 응답의 `output`은 다음 형식입니다.

```json
{"mode":"session_summary","summary":"발표 전 긴장을 느껴 첫 문장을 메모하셨습니다. 상담자는 다음 발표에도 메모를 활용해 보자고 제안했습니다.","finish_reason":"stop"}
```

### 5. 같은 계획의 다섯 회기를 마쳤을 때

다섯 번째 **회기별 요약까지 저장된 뒤**, 같은 사용자·계획에 속한 요약 다섯 개를 조회합니다. 계획 안의 회기 번호를 1부터 5까지 순서대로 붙여 아래 본문으로 4절의 제출과 2절의 조회를 반복합니다.

```json
{
  "input": {
    "mode": "plan_summary",
    "sessions": [
      {"session_number": 1, "summary": "발표할 때 첫 문장이 떠오르지 않을까 걱정했습니다."},
      {"session_number": 2, "summary": "첫 문장을 종이에 적어 두었습니다."},
      {"session_number": 3, "summary": "메모를 보며 집에서 소리 내어 연습했습니다."},
      {"session_number": 4, "summary": "동료 앞에서 첫 문장을 말해 보았습니다."},
      {"session_number": 5, "summary": "다음 발표에도 메모를 준비하기로 했습니다."}
    ]
  }
}
```

완료되면 `output.mode == "plan_summary"`를 확인하고 `output.summary`를 전체 요약으로 저장합니다. 번호 누락·중복·역순이나 빈 요약은 실패로 처리됩니다. 요약 작업의 `id`를 회기 또는 계획에 연결해 두면 화면을 다시 열거나 종료 버튼을 두 번 눌러도 같은 작업을 조회할 수 있습니다.

## 팀에서 연결할 부분

| 담당 | 구현할 동작 |
|---|---|
| 모델 · 배포 완료 | 상담 답변, 회기별 요약, 전체 요약 생성. 두 요약 모드는 각 요청에서 LoRA 강도 0을 사용합니다. |
| 백엔드 · 회기 관리 | 사용자별 계획과 그 안의 회기 1~5를 연결합니다. 대화 종료 시 회기별 요약을 요청하고, 다섯 요약이 준비되면 전체 요약을 한 번 요청합니다. 작업 상태와 결과를 저장하고 본인만 조회할 수 있게 앱에 제공합니다. |
| 백엔드 · 예약 알림 | 예를 들어 주 2회라면 사용자가 선택한 월·목 22:00과 시간대(예: `Asia/Seoul`)를 저장합니다. 서버 푸시 방식에서는 구독 기기와 예약을 연결하고, 일정 변경·해제·계획 완료 시 남은 발송을 갱신합니다. 같은 예약의 중복 발송을 막습니다. |
| 프런트엔드 · 설정과 화면 | 횟수·요일·시각 선택, 알림 권한 요청과 푸시 구독 등록, 알림을 눌렀을 때 해당 계획의 대화 화면으로 이동하는 동작을 맡습니다. 회기가 끝나면 요약 생성 중·완료·실패 상태와 결과를 보여줍니다. |

**월·목 밤 10시 예시** — 월요일 22:00에는 알림만 보냅니다. 사용자가 알림을 열고 첫 메시지를 보낼 때 상담 API를 호출합니다. 알림만 받고 대화하지 않은 날은 완료 회기에 포함하지 않습니다. 5회기 계획에서는 실제로 마친 다섯 회기를 기준으로 전체 요약을 생성합니다.

### 현재 코드에서 시작할 곳

- **모델 호출** — 기존 RunPod 함수는 `input.messages`를 제출하고 `output.reply`를 읽습니다. 제출·상태 조회를 재사용하되 요약에는 위의 모드별 입력과 출력 필드를 연결하세요. 기존 RunPod 요약 경로는 `system` 메시지를 보내므로 `RUNPOD_SUMMARY_ENABLED`만 켜서는 동작하지 않습니다. [모델 호출 코드](../backend/app/services/llm.py)
- **요약 저장** — 대화 종료 API가 이미 백그라운드 요약을 예약합니다. 기존 `Conversation.summary`는 다음 상담의 기억에 쓰는 구조화된 JSON입니다. 새 API가 반환하는 사용자용 요약 문자열은 별도 필드나 테이블에 저장하면 기존 기억 기능을 유지할 수 있습니다. 기존 `session_no`는 사용자 기준 번호이므로, 전체 요약 요청에는 해당 계획 안에서의 번호를 사용하세요. [대화 종료 처리](../backend/app/api/v1/conversations.py) · [기존 요약 처리](../backend/app/services/summary.py) · [회기 모델](../backend/app/models.py)
- **알림** — 현재 설정의 알림 스위치는 기기에 선택값만 저장합니다. 실제 발송에는 프런트의 권한·구독 처리와 백엔드의 예약·발송 연결이 필요합니다. [설정 화면](../frontend/src/pages/Settings.tsx) · [알림 설정 저장](../frontend/src/lib/preferences.ts)
