# model

## 교수님 자문 · 여기부터 보기

[면담용 핵심 자료: 실험 설명과 대표 대화 4개](CONSULTATION_GUIDE.md)

Qwen3-8B 기본 조건 → CBT 파인튜닝 → 질문 규칙 완화 → GPT 참고실험 순서로, 무엇을 바꿨고 어느 대화 구간을 보면 되는지 정리했습니다.

코드만 이 레포에서 관리합니다. 모델 가중치·데이터셋은 Hugging Face Hub 비공개 저장소에 두고, 위치를 아래에 적습니다.

- 가중치/데이터 저장소: (추가 예정)

## CTRS 평가 모델 (LLM-as-a-judge)

- [eval/ctrs_judge/README.md](eval/ctrs_judge/README.md): CTRS 6개 항목으로 상담 대화를 채점하는 평가 파이프라인과 사용법
- [검증 결과 보고](eval/ctrs_judge/docs/VALIDATION_REPORT.md): 판정 모델(gpt-6.1-sol)과 프롬프트 선정 근거, 한계

## 멀티턴 상담 반복 문제 · 실험 기록

- [연구 흐름·코드·프롬프트](eval/cbt_multiturn_experiments/README.md)
- [실험 분류와 실제 대화 결과](eval/cbt_multiturn_experiments/docs/DIALOGUE_RESULTS.md): 실험당 한 행으로 정리한 목록과 CACTUS 합성 사례 R002·R004의 전체 대화 42개입니다.

AIHub 실제 상담 발화, 전체 학습 데이터셋, 가중치와 인증정보는 포함하지 않습니다. 고정 내담자 발화 재생 실험이므로 후반의 호전 발화를 모델의 치료 효과로 해석하지 않으며, 정식 CTRS·전문가 평가 완료를 의미하지 않습니다.

## 현재 Qwen3.5-27B DPO 연구

[파이프라인·Sol 평가/생성 코드](dpo_pipeline/README.md) · [모델 주소 등록 파일](dpo_pipeline/model_release.json)

DPO 학습·최종60프로필 비교·배포는 아직 미실행입니다. 최종평가후 가중치/어댑터와 서비스endpoint 주소를 등록합니다.
