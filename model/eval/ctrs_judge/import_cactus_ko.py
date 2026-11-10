#!/usr/bin/env python3
"""번역 정제 CACTUS(한국어 1000개) json을 datasets/ jsonl로 변환함.

  python import_cactus_ko.py /path/to/cactus_selected_1000_ko_merged_final.json
결과: datasets/cactus_ko_1000.jsonl (전체, git 제외), datasets/cactus_ko_sample20.jsonl (샘플, 커밋)
"""
import argparse
import json
from pathlib import Path

from ctrs_judge.cactus_ko import convert, sample, write_jsonl

HERE = Path(__file__).resolve().parent

ap = argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("--sample-size", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()

rows = convert(json.load(open(a.source, encoding="utf-8")))
write_jsonl(rows, HERE / "datasets" / "cactus_ko_1000.jsonl")
write_jsonl(sample(rows, a.sample_size, a.seed), HERE / "datasets" / "cactus_ko_sample20.jsonl")
print(f"변환 {len(rows)}개, 샘플 {a.sample_size}개 (seed={a.seed})")
