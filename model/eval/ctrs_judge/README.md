# CTRS judge (평가 모델)

> **최종 설정**: 판정 모델 `gpt-6.1-sol`, 프롬프트 `prompts_relaxed/`(CACTUS 원본에서 엄격도 지시만 제거), 설명은 한국어. `run_eval.py`의 기본값과 같음. 선정 근거와 검증 결과는 [docs/VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md) 참고. 사람(전문가) 채점과의 비교는 아직 하지 않았음.

상담 대화를 입력받아 CTRS 항목별 점수(0~6)를 매기는 LLM-as-a-judge 파이프라인임. 작업 지침은 [CLAUDE.md](CLAUDE.md) 참고.

## 구조
- `prompts/`: 항목별 평가 프롬프트 원본(CACTUS 기준, 수정 금지). 파일 1개 = 항목 1개. 파일만 추가하면 자동으로 항목에 포함됨
- `ctrs_judge/`: 프롬프트 로더, 대화 직렬화, API 클라이언트, 파서, 실행기, 보조 지표 훅
- `models.json`: 비교할 judge 모델 설정(모델 ID, reasoning effort, temperature, 단가). 모델 추가는 항목만 넣으면 됨
- `datasets/`: 평가 대상 대화 jsonl (루트 `.gitignore`가 `data/`를 제외하므로 `datasets/`를 씀)
- `results/`: 실행 결과 jsonl

현재 항목 6개: general_1_understanding, general_2_interpersonal_effectiveness, general_3_collaboration, CBT_1_guided_discovery, CBT_2_focus, CBT_3_strategy

## 입력 형식 (jsonl, 한 줄 = 대화 1개)
```json
{"conversation_id": "cactus_0207", "turns": [{"role": "client", "text": "..."}, {"role": "therapist", "text": "..."}], "meta": {}}
```
챗봇 대화도 이 형식으로 변환만 하면 같은 파이프라인으로 채점됨.

## 데이터 (번역 정제 CACTUS 한국어 1000개)
```bash
python import_cactus_ko.py /path/to/cactus_selected_1000_ko_merged_final.json
```
- `datasets/cactus_ko_1000.jsonl`: 전체 1000개 (git 제외, 용량과 데이터 관리 정책 때문)
- `datasets/cactus_ko_sample20.jsonl`: 무작위 20개 샘플 (seed 0, 커밋됨)
- 원본의 `상담사:` / `내담자:` 줄을 turns로 변환함. conversation_id는 `cactus_ko_0000` 형식(원본 순서 기준)
- meta에는 attitude, cbt_technique, patterns, thought만 남기고 intake_form, cbt_plan은 제외함

## 평가셋 구성 (멀쩡한 20개 + 망가진 10개 + 단계별 10개 = 40개)
`python make_perturbations.py`로 만들며 API 키가 필요 없음. 결과는 `datasets/eval_set_30.jsonl`(전체 30개)과 `datasets/perturbed_10.jsonl`(망가진 10개만).
- 멀쩡한 20개: `cactus_ko_sample20.jsonl` 그대로 (meta.perturbation = original)
- 망가진 10개: 위 20개 중 10개(한 칸 건너 하나)를 골라 5유형을 돌아가며 각 2개씩 망가뜨림. 같은 원본은 한 번만 쓰고, 원본이 20개 안에 있어서 짝 비교(원본 대비 하락폭)가 가능함. id는 `원본id__유형`, meta에 `base_id`, `expected_drop`(점수 하락을 기대하는 항목)이 들어감
- 내담자 발화는 그대로 두고 상담자 발화만 바꿈. 첫 인사는 원문 유지
- **정도(severity)**: 유형마다 대화 1개씩(5개)에 대해 30%, 60% 버전(`원본id__유형_p30`, `_p60`)을 추가함. 바뀔 수 있는 상담자 발화 중 해당 비율만 망가뜨리고 나머지는 원문 그대로이며, 대화 전체에 고르게 퍼지게 결정적으로 고름. 100% 버전의 id와 내용은 기존과 동일함. `원본 -> 30% -> 60% -> 100%`로 점수가 단계적으로 내려가는지 `summarize.py`의 '정도별 점수 변화' 표로 확인함
- 파일: `eval_set_40.jsonl`(전체 40개), `perturbed_graded.jsonl`(30%, 60% 10개), `perturbed_10.jsonl`(100% 10개), `eval_set_30.jsonl`(이전 구성, 유지)
- 공감 제거(no_empathy)는 반영 문장도 함께 지워서 기대 항목에 이해를 추가함(주 항목은 대인관계)

| 유형 | 방식 | 하락 기대 항목 |
|---|---|---|
| repeat | 첫 탐색 질문을 이후 상담자 발화에 그대로 반복 (규칙) | general_1_understanding |
| no_empathy | 마지막 문장만 남겨 공감, 반영 제거 (규칙) | general_2_interpersonal_effectiveness |
| directive | 선택권 없이 일방적 지시 (템플릿 문장) | general_3_collaboration |
| lecture | 질문 대신 설교, 설득, 반박 (템플릿 문장) | CBT_1_guided_discovery |
| offtopic | 핵심 인지와 무관한 잡담 (템플릿 문장) | CBT_2_focus |
| cold (추가) | 공감 제거 + 무뚝뚝한 한마디("네.", "시간이 없으니 넘어가죠." 등)를 앞에 붙임 (규칙) | general_2_interpersonal_effectiveness |

- **차가운 태도(cold)**: 공감 제거 변형이 따뜻함 점수를 못 내려서, 말투까지 차갑게 만든 대조 버전임. 질문 내용은 공감 제거와 같고 말투만 다름. 모욕이나 욕설은 넣지 않음. `datasets/cold_extra.jsonl`(4개: 0310은 30/60/100%, 0802는 100%)이며 `eval_set_40`에는 포함되지 않고 별도로 채점함: `python3 run_eval.py --input datasets/cold_extra.jsonl --all --models gpt-6-luna gpt-6.1-sol --out results/run1.jsonl`
- 템플릿 3종은 내담자 말과 무관한 문장이라 대화 흐름이 부자연스러움. 결함이 분명히 드러나는 것이 목적이고, judge가 이 정도 결함을 구별하는지 보는 1차 검증용임
- 더 자연스러운 버전이 필요하면 `--llm-model gpt-6.1-sol`로 LLM 재작성 가능(선택, 키 필요, `perturb_prompts/` 사용)
- CBT_3_strategy에 대응하는 유형은 아직 없음

## 실행
```bash
pip install -r requirements.txt
# .env(이 폴더 또는 레포 루트)에 OPENAI_API_KEY=... 설정. 커밋 금지
python run_eval.py --input datasets/sample.jsonl --dry-run            # 호출 수만 확인
python run_eval.py --input datasets/sample.jsonl --models gpt-6-luna gpt-6.1-sol   # 기본 5개 대화만
python run_eval.py --input datasets/cactus.jsonl --all --runs 3 --out results/run1.jsonl
python -m unittest discover -s tests -v                              # API 없이 테스트
```
- 기본은 대화 5개만 채점함(비용 보호). 전체는 `--all`
- 같은 `--out`으로 다시 실행하면 완료분은 건너뛰고 이어서 진행함. API 실패 건은 재실행 시 새 줄로 추가되므로, 분석 시 같은 키의 마지막 줄을 사용할 것

## 결과 요약 (한국어, 대화 원문 제외)
```bash
python3 summarize.py results/run1.jsonl                         # 실행 요약, 점수 분포, 항목별 평균, 대화별 점수, 모델 간 일치도, 변별력, 일관성
python3 summarize.py results/run1.jsonl --csv results/run1.csv  # 엑셀용 표 (원문 제외)
python3 summarize.py results/run1.jsonl --show cactus_ko_0041 CBT_1_guided_discovery   # 점수 설명 읽기
```
- 변별력: 망가진 대화의 `expected_drop` 항목이 원본보다 내려갔는지, 나머지 항목은 얼마나 변했는지를 보여줌
- 일관성: `--runs 2` 이상으로 돌렸을 때만 출력됨

## 최종 설정으로 실행
```bash
python3 run_eval.py --input datasets/eval_set_30.jsonl --all --out results/final.jsonl     # sol + 완화 프롬프트(기본값)
python3 run_eval.py --input datasets/eval_set_30.jsonl --all --prompts-dir prompts --out results/strict.jsonl   # CACTUS 원본 엄격 프롬프트(비교용)
python3 compare_runs.py results/strict.jsonl results/final.jsonl --judge gpt-6.1-sol
python3 compare_judges.py results/strict.jsonl gpt-6-luna results/final.jsonl gpt-6.1-sol   # 서로 다른 judge의 정상 대화 순위 일치
```
- 결과 파일(`results/*.jsonl`, `*.csv`)은 대화 원문과 요청 ID가 들어 있어 git에서 제외됨

## 설명 언어 (`--lang`)
- 기본값 `--lang ko`: 프롬프트 원문은 그대로 두고, system 지시로 "설명은 한국어로, 형식은 '점수, 설명' 그대로"만 추가함. 결과 행의 `system_instruction`에 기록됨
- `--lang en`: 추가 지시 없이 원문 프롬프트만 사용 (영어로 설명하는 모델도 있음)
- 점수 기준과 엄격도 지시는 프롬프트 원문(CACTUS)에 있으며, 3번 단계 "Assign a score ... grading very strictly. If there is any deficiency, no matter how minor, assign a score of 4 or lower."가 6개 파일 모두에 들어 있음. 이 때문에 좋은 대화도 4점에 몰리는 경향이 있음

## 엄격도 문장 비교 (prompts_relaxed)
- `python3 make_relaxed_prompts.py`가 원본(`prompts/`)에서 엄격도 지시("grading very strictly ... assign a score of 4 or lower", CBT_1은 마지막 줄 포함)만 뺀 사본을 `prompts_relaxed/`에 만듦. 평가 질문, 점수 기준, 출력 형식은 그대로이고 원본은 수정하지 않음
- 실행: `python3 run_eval.py --input datasets/eval_set_30.jsonl --all --models gpt-6.1-sol --prompts-dir prompts_relaxed --out results/relaxed.jsonl` (원본 결과와 섞이지 않게 **다른 --out**을 쓸 것)
- 비교: `python3 compare_runs.py results/run1.jsonl results/relaxed.jsonl --judge gpt-6.1-sol` (정상 대화의 점수 분포, 항목별 평균, 망가진 대화의 점수 변화, 같은 칸 일치율)

## 결과 스키마 (jsonl 1줄 = 대화 x judge x 항목 x 회차)
conversation_id, conversation(원문 전문), meta, system_instruction, judge, item, run_index, score, explanation, raw_response, parse_ok, parse_error, api_error, prompt_sha256, returned_model, temperature_config, temperature_applied, reasoning_effort, input_tokens, cached_input_tokens, output_tokens, seconds, cost_usd, timestamp, metric_* (보조 지표)

## 참고
- 파싱은 첫 번째 쉼표 기준 분리, 점수는 0~6 정수만 인정함. 실패 시 원문을 `raw_response`에 보존하고 재시도하지 않음
- 일부 추론 모델은 temperature를 거부함. 이 경우 temperature 없이 재시도하고 실제 적용값을 `temperature_applied`에 기록함
- `models.json`의 단가는 기존 `cbt_multiturn_experiments` 코드의 값을 옮긴 것이므로 실행 전 확인 필요
- 원본 프롬프트 중 `[Output]` 줄은 CBT_1에만 있음. 원본 보존 원칙에 따라 그대로 둠
