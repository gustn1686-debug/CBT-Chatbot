#!/usr/bin/env python3
"""평가셋 구성 (API 불필요): 멀쩡한 20개 + 망가진 10개(100%) + 단계별 10개(5개 대화의 30%, 60%) = 40개.

- 멀쩡한 20개: datasets/cactus_ko_sample20.jsonl 그대로
- 망가뜨린 10개: 위 20개 중 10개(한 칸 건너 하나씩)를 골라 5유형을 돌아가며 각 2개씩 망가뜨림
  (같은 원본은 한 번만 사용. 짝이 되는 원본이 20개 안에 있으므로 원본 대비 하락폭을 바로 비교 가능)
정도(severity): 바뀔 수 있는 상담자 발화 중 몇 %를 망가뜨렸는지. 원본 -> 30% -> 60% -> 100%로 점수가 단계적으로 내려가는지 봄
추가: datasets/cold_extra.jsonl (차가운 태도 4개, 공감 제거 대화 기준)
출력: datasets/perturbed_10.jsonl (100% 10개), datasets/perturbed_graded.jsonl (30%, 60% 20개),
      datasets/eval_set_30.jsonl (20 + 10), datasets/eval_set_40.jsonl (20 + 10 + 10)
단계별 버전은 유형마다 첫 대화 1개씩(5개)만 만들어, 그 5개는 원본 -> 30% -> 60% -> 100% 곡선이 온전히 나옴
LLM으로 다시 쓰고 싶으면 --llm-model gpt-6.1-sol (OPENAI_API_KEY 필요, 선택 사항)
"""
import argparse
from pathlib import Path

from ctrs_judge.conversation import load_conversations
from ctrs_judge.cactus_ko import write_jsonl
from ctrs_judge.perturb import EXPECTED_DROP, as_original, make_variant

HERE = Path(__file__).resolve().parent
ORDER = ["repeat", "no_empathy", "directive", "lecture", "offtopic"]

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--input", default=str(HERE / "datasets" / "cactus_ko_sample20.jsonl"))
ap.add_argument("--n-broken", type=int, default=10)
ap.add_argument("--graded-bases", type=int, default=5, help="30%%, 60%% 버전을 만들 대화 수(앞에서부터, 유형이 한 번씩 돌아가는 5개가 기본)")
ap.add_argument("--llm-model", help="선택. 지정하면 lecture, directive, offtopic을 LLM으로 재작성")
a = ap.parse_args()

convs = load_conversations(a.input)
bases = [{"conversation_id": c.conversation_id, "turns": c.turns, "meta": c.meta} for c in convs]
if a.n_broken > len(bases):
    ap.error("망가뜨릴 수가 원본 수보다 많음")

complete = None
if a.llm_model:
    from ctrs_judge.client import JudgeClient, load_model_configs
    from run_eval import load_dotenv
    load_dotenv()
    client = JudgeClient(a.llm_model, {**load_model_configs()[a.llm_model], "max_output_tokens": 8000})
    complete = lambda p: client.complete(p).text  # noqa: E731

step = max(len(bases) // a.n_broken, 1)
picked = bases[::step][: a.n_broken]
kinds = [ORDER[k % len(ORDER)] for k in range(len(picked))]
broken = [make_variant(b, kd, complete) for b, kd in zip(picked, kinds)]
graded = [make_variant(b, kd, complete, severity=sv) for b, kd in list(zip(picked, kinds))[: a.graded_bases] for sv in (30, 60)]
originals = [as_original(b) for b in bases]

# 차가운 태도(cold): 공감 제거를 만든 대화에 말투까지 차갑게 한 버전. 첫 대화는 30/60/100%, 나머지는 100%만
cold_bases = [b for b, kd in zip(picked, kinds) if kd == "no_empathy"]
cold_rows = [make_variant(b, "cold", complete, severity=sv)
             for k, b in enumerate(cold_bases) for sv in ((30, 60, 100) if k == 0 else (100,))]
write_jsonl(cold_rows, HERE / "datasets" / "cold_extra.jsonl")

write_jsonl(broken, HERE / "datasets" / "perturbed_10.jsonl")
write_jsonl(graded, HERE / "datasets" / "perturbed_graded.jsonl")
write_jsonl(originals + broken, HERE / "datasets" / "eval_set_30.jsonl")
write_jsonl(originals + broken + graded, HERE / "datasets" / "eval_set_40.jsonl")
for r in broken + graded:
    print(f"{r['conversation_id']:36s} {r['meta']['severity']:>3d}%  기대 하락: {r['meta']['expected_drop']}")
for r in cold_rows:
    print(f"{r['conversation_id']:36s} {r['meta']['severity']:>3d}%  (추가) 기대 하락: {r['meta']['expected_drop']}")
print(f"멀쩡한 {len(originals)}개 + 망가진 {len(broken)}개 + 약한 버전 {len(graded)}개 = {len(originals) + len(broken) + len(graded)}개 -> datasets/eval_set_40.jsonl")
