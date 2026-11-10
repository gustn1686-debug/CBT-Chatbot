#!/usr/bin/env python3
"""두 결과 파일을 같은 judge로 비교함. 예)
  python3 compare_runs.py results/run1.jsonl results/relaxed.jsonl --judge gpt-6.1-sol
"""
import argparse

from ctrs_judge.analyze import compare, load_rows

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("a")
ap.add_argument("b")
ap.add_argument("--judge", default="gpt-6.1-sol")
ap.add_argument("--labels", nargs=2, default=["엄격(원본)", "완화"])
x = ap.parse_args()
print(compare(load_rows(x.a), load_rows(x.b), x.judge, *x.labels))
