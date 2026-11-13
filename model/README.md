# CBT 상담 모델 호출

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

`IN_QUEUE` 또는 `IN_PROGRESS`이면 잠시 뒤 같은 ID로 다시 조회합니다. `COMPLETED`이면 `output.reply`가 상담 답변입니다. `FAILED`, `CANCELLED`, `TIMED_OUT`이면 조회를 끝내고 실패로 처리합니다.

### 3. 다음 턴 이어가기

백엔드가 해당 사용자·회기의 이전 발화와 실제 `output.reply`를 저장합니다. 다음 턴에는 그 이력 끝에 새 `user` 발화를 붙여 같은 `/run`으로 보냅니다. 새 회기는 첫 발화부터 시작합니다.

```json
{"input":{"messages":[
  {"role":"user","content":"내일 발표가 걱정돼요."},
  {"role":"assistant","content":"발표에서 어떤 순간이 가장 걱정되시나요?"},
  {"role":"user","content":"첫 문장을 잊어버릴까 봐요."}
]}}
```
