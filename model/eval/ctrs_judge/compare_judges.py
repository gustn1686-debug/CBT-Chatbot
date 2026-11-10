#!/usr/bin/env python3
"""서로 다른 judge(또는 프롬프트)가 정상 대화의 순서를 비슷하게 매기는지 항목별 순위 상관으로 확인함. 예)
  python3 compare_judges.py results/run1.jsonl gpt-6-luna results/relaxed.jsonl gpt-6.1-sol
"""
import argparse

from ctrs_judge.analyze import load_rows, rank_agreement

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("results_a")
ap.add_argument("judge_a")
ap.add_argument("results_b")
ap.add_argument("judge_b")
x = ap.parse_args()
print(rank_agreement(load_rows(x.results_a), x.judge_a, load_rows(x.results_b), x.judge_b))
