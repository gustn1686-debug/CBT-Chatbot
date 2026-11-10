#!/usr/bin/env python3
"""결과 jsonl을 한국어 요약으로 출력함(대화 원문 제외).

  python summarize.py results/run1.jsonl
  python summarize.py results/run1.jsonl --csv results/run1.csv      # 엑셀용 표
  python summarize.py results/run1.jsonl --show cactus_ko_0041       # 설명 읽기
  python summarize.py results/run1.jsonl --show cactus_ko_0041 CBT_1_guided_discovery
"""
import argparse

from ctrs_judge.analyze import explanations, load_rows, summarize, to_csv

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("results")
ap.add_argument("--csv", help="요약용 csv 저장 경로(원문 제외, 엑셀 호환)")
ap.add_argument("--show", nargs="+", metavar=("CONV_ID", "ITEM"), help="대화(와 항목)의 점수 설명을 출력")
a = ap.parse_args()

rows = load_rows(a.results)
if a.show:
    print(explanations(rows, a.show[0], a.show[1] if len(a.show) > 1 else None))
else:
    print(summarize(rows))
if a.csv:
    to_csv(rows, a.csv)
    print(f"csv 저장: {a.csv}")
