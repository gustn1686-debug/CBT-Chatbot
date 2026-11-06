# 프롬프트와 코드 대응

| 역할 | 실제 텍스트 | 코드 |
| --- | --- | --- |
| 회기 CTRS 원6척도 | [6개 txt](../cbt_dpo/rubrics) | [judge.py](../cbt_dpo/judge.py): render_prompt, validate, evaluate_item |
| 한국어 원출력 지시 | [ctrs_instructions.txt](../prompts/ctrs_instructions.txt) | judge.INSTRUCTIONS |
| 언어·턴 근거 추가 | [ctrs_addendum.txt](../prompts/ctrs_addendum.txt) | judge.ADDENDUM |
| 사전 정보 제공 방식 | [conversation.py](../cbt_dpo/conversation.py) | Conversation.to_judge_text |
| GPT 대안 생성 | [editor_system.txt](../prompts/editor_system.txt), [wrapper](../prompts/editor_wrapper.txt) | [generation.py](../cbt_dpo/generation.py) |
| 양순서 선호·언어 | [preference_system.txt](../prompts/preference_system.txt) | [preference.py](../cbt_dpo/preference.py) |
| Qwen 상담 프롬프트 | [counselor_system.txt](../prompts/counselor_system.txt) | generation.build_scene의실제DPO prompt |
| 코호트·지적턴·교체 | 고정 코호트와 CTRS 출력 | [pipeline.py](../cbt_dpo/pipeline.py) |
| 실행·캐시·한도 | Sol low / fresh_context | [backend.py](../cbt_dpo/backend.py) |

출력JSON 스키마3개도 [prompts](../prompts)에 둔다. 실제 CTRS 입력은 한국어 원출력 지시 + 원래항목의 전체 채점본문(사전자료·회기 포함) + 추가언어/턴지침 + 근거위치표로 구성한다. 부가 필드만 보고 원래 채점본문을 생략하면 같은 평가가 아니다.

기존 연구용 파일의 긴 import 연결과 특정 맥 경로를 공개 코드로 가져오지 않았다. 대신 현재 역할·입력을 독립 구현에 이식하고 원본과 오프라인 대조했다. 과거의3턴제한·프로젝트원인태그 평가기는 현재실행 경로에 포함하지 않는다. 원본파일 해시는 provenance.json으로 추적한다.

인용 검증 실패 시 자동 재채점하지 않는다. 원출력은 보존하며 같은 발화의 정확한 인용만 정렬하는 quote_audits와, 회기 전체 근거의 유일한 실제 인용 출처 번호만 정렬하는 evidence_source_audits를 구분한다. 점수·판정·문제대상·이유·힌트나 개별턴의 미래 근거를 바꿀 수 없다. 과거에새감사2건을적용했으며전문가정답검증을뜻하지않는다.
