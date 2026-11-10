# 실행 노트

Python3.10이상과 표준라이브러리로 오프라인 작업·테스트를 수행한다. 실제 Sol 호출만 ChatGPT로 로그인한 `codex` CLI와 포함 사용 한도가 필요하다. CLI버전은 호출 캐시에 기록한다. API 키를 읽거나 API로 전환하지 않는다. 이식본의 실제 모델 호출은 아직 실행하지 않았다.

저장소 루트에서:

```bash
export PYTHONPATH="$PWD/model/dpo_pipeline"
python3 -m unittest discover -s model/dpo_pipeline/tests -v
python3 -m cbt_dpo render model/dpo_pipeline/examples/session.json /private/tmp/cbt-dpo-render
```

render는 모델을 호출하지 않고 실제6항목 입력을 저장한다. 외부 프로필·회기 데이터는 아래 예시 형식을 따른다. provided_context는 상담자가 실제 받은 자료와 반드시 일치해야 한다.

실제 호출은 명시한 명령에서만 발생한다. 아래는 사용자가 별도로 실행할 때의 절차이며 이PR 작성 중에는 실행하지 않았다.

```bash
python3 -m cbt_dpo evaluate session.json runs/baseline --execute
# scores.jsonl: conversation_id,item,score,parse_ok의6행/회기.
# 여러회기의원점수파일에서코호트를한번고정한다.
python3 -m cbt_dpo freeze-cohort scores.jsonl runs/cohort.json
python3 -m cbt_dpo prepare session.json runs/baseline model/dpo_pipeline/prompts/counselor_system.txt runs/cohort.json runs/scenes.json
python3 -m cbt_dpo generate runs/scenes.json runs/rewrite --execute
python3 -m cbt_dpo compare runs/scenes.json runs/rewrite --execute
python3 -m cbt_dpo edit-session session.json runs/rewrite/preference_candidates.jsonl runs/edited.json
python3 -m cbt_dpo evaluate runs/edited.json runs/edited-score --execute
```

세션별 출력 폴더를 구분한다. 코호트는 과거 원점수로 먼저 고정할 수도 있으며 이후 재채점으로 바꾸지 않는다. 현재코드는코호트의회기ID와원점수파일해시를보존한다. 새자료에이전원점수와다른평가버전을섞어수정효과로계산하지않는다.

prepare는지적턴전체를시점제한입력으로바꾸며개수상한은없다. 비교배치의입력크기는백엔드120KB제한을따른다. 초과시중단하며,대상을버리거나기준을자동변경하지않는다. 향후더긴회기에서는고정배치분할을별도기록해야한다.

수신캐시는재사용한다. pending_or_unknown은재호출을차단한다. 포함한도에실제로제공된창만검사하며97%이상·잔량불명확·서버제한이면중단한다. 구매크레딧·한도리셋·유료API·GPU·DPO학습·자동재개는사용하지않는다. 생성응답이빈값/2000자초과면자동재생성하지않는다.

상담생성 서버·DPO학습기·최종60프로필 생성기는 이패키지의실행범위가아니다. 이폴더의CLI만으로DPO가학습되거나서비스가시작되는것은아니다. 선호쌍은자동평가후보로training_ready=false이며원시프로필·대화·캐시는runs등의비공개외부폴더에서관리한다.
