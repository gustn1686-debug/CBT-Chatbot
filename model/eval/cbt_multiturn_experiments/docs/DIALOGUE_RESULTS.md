# CACTUS 2개의 멀티턴 사례로 보는 모델 성능

처음 보거나 면담 자료를 찾는다면 [실험 설명과 대표 대화 4개](../../../CONSULTATION_GUIDE.md)부터 확인하세요.

정리일: 2026-10-09

내담자 발화는 한국어로 번역·정제한 CACTUS 합성 대화의 고정 입력이다.

## 실험별 요약


| 실험 | 어떤 실험인가? | 간단한 설명 | 대화록 수 | 설정·결과 |
|---|---|---|---:|---|
| E03 | [하네스 비교] 상담 계획·상태 관리 | Qwen3-8B 기본·파인튜닝 모델에 상담 계획과 진행 메모를 추가해 반복이 줄어드는지 확인. | 4 | [보기](../experiments/E03_plan_state/README.md) |
| E04 | [프롬프트 비교] 프롬프트 영향 분리 | 계획·상태 기능 없이 기본·파인튜닝 모델에 기존/v2 프롬프트를 적용해 네 조건 비교. | 8 | [보기](../experiments/E04_prompt_ablation/README.md) |
| E05 | [참고실험] GPT 상담자 참고 실험 | GPT Luna를 상담자로 사용해 같은 내담자 발화에 대한 대화 진행을 참고 비교. | 1 | [보기](../experiments/E05_gpt_counselor/README.md) |
| E06 | [프롬프트 비교] 질문 규칙 완화 | 질문·연습 제안 규칙을 완화해 매번 질문하는 경향이 달라지는지 확인. | 2 | [보기](../experiments/E06_question_rules/README.md) |
| E07 | [프롬프트 비교] 재동의 질문 방지 | 파인튜닝 모델에 이미 동의한 개입을 다시 제안하지 않도록 지침을 추가. | 1 | [보기](../experiments/E07_no_reconsent/README.md) |
| E08 | [프롬프트 비교] 대화 전환 예시 추가 | 사고 전환 뒤 적용·정리로 넘어가는 예시를 넣은 조건과 예시 없는 조건 비교. | 8 | [보기](../experiments/E08_transition_examples/README.md) |
| E09 | [모델 비교] Gemma·Qwen9B 비교 | CBT 추가 파인튜닝 없이 Gemma 4 31B와 Qwen3.5-9B의 상담 흐름 비교. | 4 | [보기](../experiments/E09_gemma_qwen9b/README.md) |
| E10 | [모델 비교] Qwen27B 추가 비교 | 같은 고정 내담자 발화와 프롬프트로 Qwen3.5-27B의 상담 흐름 확인. | 2 | [보기](../experiments/E10_qwen27b/README.md) |
| E11 | [모델 비교] Mistral·EXAONE 비교 | 두 모델을 결정적 생성과 샘플링 조건으로 실행해 반복·출력 길이 문제 비교. | 8 | [보기](../experiments/E11_mistral_exaone/README.md) |
| E12 | [모델 비교] Llama 두 모델 비교 | 같은 프롬프트로 Llama 3·3.1 8B의 반복과 사고 전환 이후 응답 비교. | 4 | [보기](../experiments/E12_llama/README.md) |

## 조건별 전체 대화

`base`는 CBT 추가 파인튜닝 어댑터를 적용하지 않은 조건, `tuned`는 적용한 조건이다. R002는 수영 경기 후 부족감, R004는 언어 학습의 한계에 관한 합성 사례다.

### E03 · [하네스 비교] 상담 계획·상태 관리

- plan_state / base · R002 · 14대화쌍: [전체 대화](../experiments/E03_plan_state/results/plan_state_base_R002.md)
- plan_state / tuned · R002 · 14대화쌍: [전체 대화](../experiments/E03_plan_state/results/plan_state_tuned_R002.md)
- plan_state / base · R004 · 15대화쌍: [전체 대화](../experiments/E03_plan_state/results/plan_state_base_R004.md)
- plan_state / tuned · R004 · 15대화쌍: [전체 대화](../experiments/E03_plan_state/results/plan_state_tuned_R004.md)

### E04 · [프롬프트 비교] 프롬프트 영향 분리

- original / base · R002 · 14대화쌍: [전체 대화](../experiments/E04_prompt_ablation/results/original_base_R002.md)
- original / tuned · R002 · 14대화쌍: [전체 대화](../experiments/E04_prompt_ablation/results/original_tuned_R002.md)
- original / base · R004 · 15대화쌍: [전체 대화](../experiments/E04_prompt_ablation/results/original_base_R004.md)
- original / tuned · R004 · 15대화쌍: [전체 대화](../experiments/E04_prompt_ablation/results/original_tuned_R004.md)
- v2 / base · R002 · 14대화쌍: [전체 대화](../experiments/E04_prompt_ablation/results/v2_base_R002.md)
- v2 / tuned · R002 · 14대화쌍: [전체 대화](../experiments/E04_prompt_ablation/results/v2_tuned_R002.md)
- v2 / base · R004 · 15대화쌍: [전체 대화](../experiments/E04_prompt_ablation/results/v2_base_R004.md)
- v2 / tuned · R004 · 15대화쌍: [전체 대화](../experiments/E04_prompt_ablation/results/v2_tuned_R004.md)

### E05 · [참고실험] GPT 상담자 참고 실험

- gpt_luna · R002 · 14대화쌍: [전체 대화](../experiments/E05_gpt_counselor/results/gpt_luna_gpt_luna_R002.md)

### E06 · [프롬프트 비교] 질문 규칙 완화

- relaxed / base · R002 · 14대화쌍: [전체 대화](../experiments/E06_question_rules/results/relaxed_base_R002.md)
- relaxed / tuned · R002 · 14대화쌍: [전체 대화](../experiments/E06_question_rules/results/relaxed_tuned_R002.md)

### E07 · [프롬프트 비교] 재동의 질문 방지

- no_reconsent / tuned · R002 · 14대화쌍: [전체 대화](../experiments/E07_no_reconsent/results/no_reconsent_tuned_R002.md)

### E08 · [프롬프트 비교] 대화 전환 예시 추가

- control / base · R002 · 14대화쌍: [전체 대화](../experiments/E08_transition_examples/results/control_base_R002.md)
- control / tuned · R002 · 14대화쌍: [전체 대화](../experiments/E08_transition_examples/results/control_tuned_R002.md)
- control / base · R004 · 15대화쌍: [전체 대화](../experiments/E08_transition_examples/results/control_base_R004.md)
- control / tuned · R004 · 15대화쌍: [전체 대화](../experiments/E08_transition_examples/results/control_tuned_R004.md)
- examples / base · R002 · 14대화쌍: [전체 대화](../experiments/E08_transition_examples/results/examples_base_R002.md)
- examples / tuned · R002 · 14대화쌍: [전체 대화](../experiments/E08_transition_examples/results/examples_tuned_R002.md)
- examples / base · R004 · 15대화쌍: [전체 대화](../experiments/E08_transition_examples/results/examples_base_R004.md)
- examples / tuned · R004 · 15대화쌍: [전체 대화](../experiments/E08_transition_examples/results/examples_tuned_R004.md)

### E09 · [모델 비교] Gemma·Qwen9B 비교

- gemma4_31b · R002 · 14대화쌍: [전체 대화](../experiments/E09_gemma_qwen9b/results/gemma4_31b_gemma4_31b_R002.md)
- gemma4_31b · R004 · 15대화쌍: [전체 대화](../experiments/E09_gemma_qwen9b/results/gemma4_31b_gemma4_31b_R004.md)
- qwen35_9b · R002 · 14대화쌍: [전체 대화](../experiments/E09_gemma_qwen9b/results/qwen35_9b_qwen35_9b_R002.md)
- qwen35_9b · R004 · 15대화쌍: [전체 대화](../experiments/E09_gemma_qwen9b/results/qwen35_9b_qwen35_9b_R004.md)

### E10 · [모델 비교] Qwen27B 추가 비교

- qwen35_27b · R002 · 14대화쌍: [전체 대화](../experiments/E10_qwen27b/results/qwen35_27b_qwen35_27b_R002.md)
- qwen35_27b · R004 · 15대화쌍: [전체 대화](../experiments/E10_qwen27b/results/qwen35_27b_qwen35_27b_R004.md)

### E11 · [모델 비교] Mistral·EXAONE 비교

- mistral32_24b_greedy · R002 · 14대화쌍: [전체 대화](../experiments/E11_mistral_exaone/results/mistral32_24b_greedy_mistral32_24b_greedy_R002.md)
- mistral32_24b_greedy · R004 · 15대화쌍: [전체 대화](../experiments/E11_mistral_exaone/results/mistral32_24b_greedy_mistral32_24b_greedy_R004.md)
- mistral32_24b_sampled · R002 · 14대화쌍: [전체 대화](../experiments/E11_mistral_exaone/results/mistral32_24b_sampled_mistral32_24b_sampled_R002.md)
- mistral32_24b_sampled · R004 · 15대화쌍: [전체 대화](../experiments/E11_mistral_exaone/results/mistral32_24b_sampled_mistral32_24b_sampled_R004.md)
- exaone4_32b_greedy · R002 · 14대화쌍: [전체 대화](../experiments/E11_mistral_exaone/results/exaone4_32b_greedy_exaone4_32b_greedy_R002.md)
- exaone4_32b_greedy · R004 · 15대화쌍: [전체 대화](../experiments/E11_mistral_exaone/results/exaone4_32b_greedy_exaone4_32b_greedy_R004.md)
- exaone4_32b_sampled · R002 · 14대화쌍: [전체 대화](../experiments/E11_mistral_exaone/results/exaone4_32b_sampled_exaone4_32b_sampled_R002.md)
- exaone4_32b_sampled · R004 · 15대화쌍: [전체 대화](../experiments/E11_mistral_exaone/results/exaone4_32b_sampled_exaone4_32b_sampled_R004.md)

### E12 · [모델 비교] Llama 두 모델 비교

- llama3_8b · R002 · 14대화쌍: [전체 대화](../experiments/E12_llama/results/llama3_8b_llama3_8b_R002.md)
- llama3_8b · R004 · 15대화쌍: [전체 대화](../experiments/E12_llama/results/llama3_8b_llama3_8b_R004.md)
- llama31_8b · R002 · 14대화쌍: [전체 대화](../experiments/E12_llama/results/llama31_8b_llama31_8b_R002.md)
- llama31_8b · R004 · 15대화쌍: [전체 대화](../experiments/E12_llama/results/llama31_8b_llama31_8b_R004.md)
