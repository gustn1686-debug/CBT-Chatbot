#!/usr/bin/env python3
"""prompts/ 원본에서 엄격도 지시만 뺀 비교용 프롬프트를 prompts_relaxed/에 만듦(원본은 그대로).

제거하는 것:
  - 단계 3의 "grading very strictly (and uptight). If there is any deficiency, no matter how minor, assign a score of 4 or lower."
    -> "Assign a score based on the criteria."
  - CBT_1 마지막 줄 "Do not forget to give a score strictly and uptight."
평가 질문, 점수 기준, 출력 형식, {conversation} 자리는 모두 그대로임.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC, DST = HERE / "prompts", HERE / "prompts_relaxed"
DST.mkdir(exist_ok=True)

STEP3 = re.compile(r"Assign a score based on the criteria, grading very strictly(?: and uptight)?\. "
                   r"If there is any deficiency, no matter how minor, assign a score of 4 or lower\.")
TAIL = re.compile(r"\n?Do not forget to give a score strictly and uptight\.\s*", re.IGNORECASE)

for f in sorted(SRC.glob("*.txt")):
    t = f.read_text(encoding="utf-8")
    t2, n = STEP3.subn("Assign a score based on the criteria.", t)
    if n != 1:
        raise SystemExit(f"{f.name}: 단계 3 문장을 찾지 못함({n}건)")
    t2 = TAIL.sub("\n", t2) if f.name.startswith("CBT_1") else t2
    (DST / f.name).write_text(t2, encoding="utf-8")
    print(f"{f.name}: 엄격도 문장 제거" + (" + 마지막 줄 제거" if t2 != t.replace(STEP3.search(t).group(0), 'Assign a score based on the criteria.') else ""))
