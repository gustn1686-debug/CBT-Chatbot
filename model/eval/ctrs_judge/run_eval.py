#!/usr/bin/env python3
"""CTRS judge 실행. 기본은 대화 5개만 채점함(비용 보호). 전체 실행은 --all.

예)
  python run_eval.py --input datasets/sample.jsonl --models gpt-6-luna gpt-6.1-sol
  python run_eval.py --input datasets/cactus_original.jsonl --all --runs 3 --out results/run1.jsonl
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from ctrs_judge.client import JudgeClient, load_model_configs
from ctrs_judge.conversation import load_conversations
from ctrs_judge.prompts import load_prompts
from ctrs_judge.runner import run

HERE = Path(__file__).resolve().parent
KO_INSTRUCTIONS = ("평가 설명(explanation)은 반드시 한국어로 작성하세요. "
                   "출력 형식은 사용자 지시 그대로 '점수, 설명' 한 줄이며, 점수는 숫자만 쓰고 접두어를 붙이지 마세요.")


def load_dotenv() -> None:
    # 의존성 없이 .env를 읽음(이 폴더 또는 레포 루트). 이미 설정된 환경변수는 덮어쓰지 않음
    for p in (HERE / ".env", HERE.parents[2] / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="대화 jsonl")
    ap.add_argument("--models", nargs="+", default=["gpt-6.1-sol"], help="models.json의 키 (기본: 최종 선정 판정자 gpt-6.1-sol)")
    ap.add_argument("--models-file", default=str(HERE / "models.json"))
    ap.add_argument("--items", nargs="*", help="일부 항목만(파일명 stem). 기본은 prompts/ 전체")
    ap.add_argument("--prompts-dir", default=str(HERE / "prompts_relaxed"),
                    help="기본: prompts_relaxed(최종 선정, 엄격도 문장 제거). CACTUS 원본 엄격 프롬프트는 --prompts-dir prompts")
    ap.add_argument("--limit", type=int, default=5, help="앞에서부터 N개 대화만(기본 5)")
    ap.add_argument("--all", action="store_true", help="--limit 무시하고 전체 대화 실행")
    ap.add_argument("--runs", type=int, default=1, help="같은 대화 반복 채점 횟수(일관성 측정용)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", help="결과 jsonl 경로. 같은 경로로 재실행하면 이어서 진행")
    ap.add_argument("--lang", choices=["ko", "en"], default="ko",
                    help="ko(기본): 설명을 한국어로 쓰라는 system 지시를 추가(프롬프트 원문은 그대로). en: 추가 지시 없음")
    ap.add_argument("--dry-run", action="store_true", help="API 호출 없이 호출 수만 출력")
    a = ap.parse_args()

    load_dotenv()
    convs = load_conversations(a.input, None if a.all else a.limit)
    items = load_prompts(a.prompts_dir, a.items)
    cfgs = load_model_configs(a.models_file)
    unknown = [m for m in a.models if m not in cfgs]
    if unknown:
        ap.error(f"models.json에 없는 모델: {unknown}")

    calls = len(convs) * len(items) * len(a.models) * a.runs
    print(f"대화 {len(convs)}개 x 항목 {len(items)}개({[i.item for i in items]}) x 모델 {a.models} "
          f"x 회차 {a.runs} = API 호출 {calls}회")
    if a.dry_run:
        return
    if not os.environ.get("OPENAI_API_KEY") and any(
            "base_url" not in cfgs[m] and "base_url_env" not in cfgs[m] for m in a.models):
        ap.error("OPENAI_API_KEY가 없음(.env에 설정)")

    out = Path(a.out) if a.out else HERE / "results" / f"{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    instructions = KO_INSTRUCTIONS if a.lang == "ko" else None
    judges = {m: (cfgs[m], JudgeClient(m, cfgs[m], instructions=instructions).complete) for m in a.models}
    stats = run(convs, items, judges, out, a.runs, a.workers, extra_fields={"system_instruction": instructions})
    print(f"저장: {out}\n{stats}")


if __name__ == "__main__":
    main()
