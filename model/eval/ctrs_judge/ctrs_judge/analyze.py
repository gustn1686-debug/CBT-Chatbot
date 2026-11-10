"""결과 jsonl 요약. 대화 원문 없이 점수, 일치도, 변별력, 일관성을 한국어로 출력함."""
from __future__ import annotations

import json
import statistics as st
import unicodedata
from collections import defaultdict
from pathlib import Path

from .perturb import EXPECTED_ITEMS

ITEM_KO = {
    "general_1_understanding": "이해",
    "general_2_interpersonal_effectiveness": "대인관계",
    "general_3_collaboration": "협력",
    "CBT_1_guided_discovery": "유도된 발견",
    "CBT_2_focus": "핵심 초점",
    "CBT_3_strategy": "변화전략",
}
ITEM_ORDER = list(ITEM_KO)
TYPE_KO = {"repeat": "반복", "no_empathy": "공감 제거", "directive": "일방적 지시",
           "lecture": "설교", "offtopic": "잡담", "cold": "차가운 태도"}


def ko(item: str) -> str:
    return ITEM_KO.get(item, item)


def width(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def pad(s, w: int, right: bool = False) -> str:
    s = str(s)
    gap = max(w - width(s), 0)
    return " " * gap + s if right else s + " " * gap


def table(header: list[str], rows: list[list], right_from: int = 1) -> str:
    cols = list(zip(header, *rows)) if rows else [(h,) for h in header]
    ws = [max(width(c) for c in col) for col in cols]
    line = lambda r: "  ".join(pad(c, ws[i], right=i >= right_from) for i, c in enumerate(r))  # noqa: E731
    return "\n".join([line(header), "  ".join("-" * w for w in ws)] + [line(r) for r in rows])


def load_rows(path: Path | str) -> list[dict]:
    """같은 (대화, judge, 항목, 회차)는 마지막 줄을 사용하되, 성공 줄을 실패 줄로 덮지 않음."""
    best: dict[tuple, dict] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        k = (r["conversation_id"], r["judge"], r["item"], r["run_index"])
        if k in best and best[k].get("api_error") is None and r.get("api_error") is not None:
            continue
        best[k] = r
    return list(best.values())


def _items(rows: list[dict]) -> list[str]:
    present = {r["item"] for r in rows}
    return [i for i in ITEM_ORDER if i in present] + sorted(present - set(ITEM_ORDER))


def score_means(rows: list[dict]) -> dict[tuple, float]:
    """(대화, judge, 항목) -> 회차 평균 점수 (파싱 성공 건만)"""
    acc = defaultdict(list)
    for r in rows:
        if r.get("parse_ok") and r.get("score") is not None:
            acc[(r["conversation_id"], r["judge"], r["item"])].append(r["score"])
    return {k: sum(v) / len(v) for k, v in acc.items()}


def fmt(x: float | None) -> str:
    if x is None:
        return "-"
    return str(int(x)) if abs(x - round(x)) < 1e-9 else f"{x:.1f}"


def summarize(rows: list[dict]) -> str:
    out = []
    judges = sorted({r["judge"] for r in rows})
    items = _items(rows)
    means = score_means(rows)
    meta = {r["conversation_id"]: r.get("meta", {}) for r in rows}

    # 1. 실행 요약
    t = []
    for j in judges:
        rs = [r for r in rows if r["judge"] == j]
        ok = sum(1 for r in rs if r.get("parse_ok"))
        api = sum(1 for r in rs if r.get("api_error"))
        cost = sum(r.get("cost_usd") or 0 for r in rs)
        secs = [r["seconds"] for r in rs if r.get("seconds")]
        temp = {r.get("temperature_applied") for r in rs if not r.get("api_error")}
        t.append([j, len(rs), ok, len(rs) - ok - api, api, f"${cost:.4f}",
                  f"{sum(secs) / len(secs):.1f}초" if secs else "-",
                  "미적용" if temp == {None} else ("적용" if None not in temp else "일부")])
    out += ["■ 실행 요약", table(["모델", "호출", "파싱성공", "파싱실패", "API실패", "비용", "평균시간", "temperature"], t), ""]

    # 2. 점수 분포
    t = []
    for j in judges:
        sc = [r["score"] for r in rows if r["judge"] == j and r.get("parse_ok")]
        t.append([j] + [sum(1 for s in sc if s == k) for k in range(7)] + [f"{sum(sc) / len(sc):.2f}" if sc else "-"])
    out += ["■ 점수 분포 (건수)", table(["모델"] + [f"{k}점" for k in range(7)] + ["평균"], t), ""]

    # 3. 항목별 평균
    t = []
    for it in items:
        row = [ko(it)]
        for j in judges:
            v = [m for (c, jj, ii), m in means.items() if jj == j and ii == it]
            row.append(f"{sum(v) / len(v):.2f}" if v else "-")
        t.append(row)
    out += ["■ 항목별 평균 점수", table(["항목"] + judges, t), ""]

    # 4. 대화별 점수
    convs = sorted({r["conversation_id"] for r in rows})
    if len(convs) <= 60:
        t = []
        for c in convs:
            tag = meta[c].get("perturbation", "")
            tag = "원본" if tag in ("", "original") else TYPE_KO.get(tag, tag)
            for j in judges:
                t.append([c, tag, j] + [fmt(means.get((c, j, it))) for it in items])
        out += ["■ 대화별 점수", table(["대화", "유형", "모델"] + [ko(i) for i in items], t, right_from=3), ""]

    # 5. 모델 간 일치도
    for a in range(len(judges)):
        for b in range(a + 1, len(judges)):
            ja, jb = judges[a], judges[b]
            pairs = [(means[(c, ja, i)], means[(c, jb, i)]) for (c, j, i) in means
                     if j == ja and (c, jb, i) in means]
            if pairs:
                d = [x - y for x, y in pairs]
                same = sum(1 for x in d if abs(x) < 1e-9)
                near = sum(1 for x in d if abs(x) <= 1 + 1e-9)
                out += [f"■ 모델 간 일치도 ({ja} vs {jb})",
                        f"  비교 {len(pairs)}건, 정확히 같음 {same}건({same / len(pairs):.0%}), "
                        f"±1점 이내 {near}건({near / len(pairs):.0%}), 평균 차이({ja}-{jb}) {sum(d) / len(d):+.2f}점", ""]

    # 6. 변별력 (원본 대비 망가진 버전)
    broken = [c for c in convs if meta[c].get("perturbation") not in (None, "", "original")]
    if broken:
        t, per_judge = [], defaultdict(lambda: {"exp": [], "oth": []})
        dose = defaultdict(list)  # (유형, 모델, 정도) -> 기대 항목 평균 변화
        dose_oth = defaultdict(list)
        for c in broken:
            base, kind = meta[c].get("base_id"), meta[c]["perturbation"]
            sev = meta[c].get("severity", 100)
            exp_items = EXPECTED_ITEMS.get(kind) or ([meta[c]["expected_drop"]] if meta[c].get("expected_drop") else [])
            for j in judges:
                exp = [i for i in exp_items if (base, j, i) in means and (c, j, i) in means]
                if not exp:
                    continue
                d_exp = [means[(c, j, i)] - means[(base, j, i)] for i in exp]
                others = [means[(c, j, i)] - means[(base, j, i)] for i in items
                          if i not in exp_items and (c, j, i) in means and (base, j, i) in means]
                dose[(kind, j, sev)].append(sum(d_exp) / len(d_exp))
                if others:
                    dose_oth[(kind, j, sev)].append(sum(others) / len(others))
                if sev == 100:
                    i0 = exp[0]
                    t.append([c, TYPE_KO.get(kind, kind), j, "+".join(ko(i) for i in exp), fmt(means[(base, j, i0)]),
                              fmt(means[(c, j, i0)]), f"{sum(d_exp) / len(d_exp):+.1f}",
                              f"{sum(others) / len(others):+.2f}" if others else "-"])
                    per_judge[j]["exp"].append(sum(d_exp) / len(d_exp))
                    per_judge[j]["oth"] += others
        out += ["■ 변별력 (정도 100%, 원본 대비 기대 항목 변화)",
                table(["망가진 대화", "유형", "모델", "기대 항목", "원본", "망가짐", "변화", "다른 항목 평균변화"], t, right_from=4), ""]
        for j, d in per_judge.items():
            e = d["exp"]
            down = sum(1 for x in e if x < 0)
            line = f"  {j}: 기대 항목 평균 변화 {sum(e) / len(e):+.2f}점, 하락한 건 {down}/{len(e)}"
            if d["oth"]:
                line += f", 나머지 항목 평균 변화 {sum(d['oth']) / len(d['oth']):+.2f}점"
            out.append(line)
        out.append("")
        sevs = sorted({k[2] for k in dose})
        if len(sevs) > 1:  # 정도별 점수 변화 (원본 -> 30% -> 60% -> 100%)
            t = []
            for kind in [k for k in EXPECTED_ITEMS if any(kk[0] == k for kk in dose)]:
                for j in judges:
                    cells = []
                    for sv in sevs:
                        v = dose.get((kind, j, sv))
                        cells.append(f"{sum(v) / len(v):+.1f} (n={len(v)})" if v else "-")
                    t.append([TYPE_KO.get(kind, kind), j] + cells)
            allrow = []
            for j in judges:
                cells = []
                for sv in sevs:
                    v = [x for (kd, jj, s2), vs in dose.items() if jj == j and s2 == sv for x in vs]
                    o = [x for (kd, jj, s2), vs in dose_oth.items() if jj == j and s2 == sv for x in vs]
                    cells.append(f"{sum(v) / len(v):+.2f} / {sum(o) / len(o):+.2f}" if v and o else "-")
                allrow.append(["전체 (기대/나머지)", j] + cells)
            out += ["■ 정도별 점수 변화 (원본 대비, 기대 항목 평균. 정도가 클수록 더 내려가야 정상)",
                    table(["유형", "모델"] + [f"{s_}%" for s_ in sevs], t + allrow, right_from=2), ""]

    # 7. 일관성 (반복 채점)
    groups = defaultdict(list)
    for r in rows:
        if r.get("parse_ok"):
            groups[(r["conversation_id"], r["judge"], r["item"])].append(r["score"])
    rep = {k: v for k, v in groups.items() if len(v) > 1}
    if rep:
        t = []
        for j in judges:
            vs = [v for (c, jj, i), v in rep.items() if jj == j]
            if vs:
                sd = [st.pstdev(v) for v in vs]
                t.append([j, len(vs), f"{sum(sd) / len(sd):.2f}",
                          f"{sum(1 for v in vs if len(set(v)) > 1) / len(vs):.0%}"])
        out += ["■ 일관성 (같은 대화를 반복 채점)", table(["모델", "반복 조합 수", "평균 표준편차", "점수가 달라진 비율"], t), ""]

    return "\n".join(out).rstrip() + "\n"


def explanations(rows: list[dict], conversation_id: str, item: str | None = None) -> str:
    out = []
    for r in sorted(rows, key=lambda r: (r["item"], r["judge"], r["run_index"])):
        if r["conversation_id"] == conversation_id and (item is None or r["item"] == item):
            out.append(f"[{r['judge']} / {ko(r['item'])} / {r['run_index']}회차] {r.get('score')}점\n  {r.get('explanation') or r.get('api_error')}\n")
    return "\n".join(out) or "해당하는 결과가 없음\n"


def to_csv(rows: list[dict], path: Path | str) -> None:
    import csv
    cols = ["conversation_id", "judge", "item", "run_index", "score", "parse_ok", "cost_usd", "seconds",
            "temperature_applied", "explanation"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: 엑셀에서 한글 깨짐 방지
        w = csv.writer(f)
        w.writerow(cols + ["perturbation", "base_id"])
        for r in sorted(rows, key=lambda r: (r["conversation_id"], r["judge"], r["item"], r["run_index"])):
            m = r.get("meta", {})
            w.writerow([r.get(c) for c in cols] + [m.get("perturbation"), m.get("base_id")])


def compare(rows_a: list[dict], rows_b: list[dict], judge: str, label_a: str, label_b: str) -> str:
    """같은 judge의 두 실행(예: 원본 프롬프트 vs 엄격도 문장 제거)을 비교함."""
    out = []
    runs = {label_a: [r for r in rows_a if r["judge"] == judge], label_b: [r for r in rows_b if r["judge"] == judge]}
    ma, mb = (score_means(runs[label_a]), score_means(runs[label_b]))
    meta = {r["conversation_id"]: r.get("meta", {}) for rs in runs.values() for r in rs}
    common = sorted({c for (c, j, i) in ma} & {c for (c, j, i) in mb})
    is_orig = lambda c: meta[c].get("perturbation") in (None, "", "original")  # noqa: E731
    origs = [c for c in common if is_orig(c)]
    broken = [c for c in common if not is_orig(c) and meta[c].get("severity", 100) == 100]
    items = _items(runs[label_a] + runs[label_b])
    out.append(f"비교 대상: {judge} / 공통 대화 {len(common)}개 (정상 {len(origs)}, 망가진 100% {len(broken)})\n")

    def dist(m, convs):
        sc = [round(m[(c, judge, i)]) for c in convs for i in items if (c, judge, i) in m]
        return sc

    t = []
    for lab, m in ((label_a, ma), (label_b, mb)):
        sc = dist(m, origs)
        t.append([lab] + [sum(1 for s in sc if s == k) for k in range(7)] +
                 [f"{sum(sc) / len(sc):.2f}", f"{st.pstdev(sc):.2f}", len({s for s in sc})])
    out += ["■ 정상 대화의 점수 분포 (퍼질수록 좋은 대화끼리 구분 가능)",
            table(["프롬프트"] + [f"{k}점" for k in range(7)] + ["평균", "표준편차", "서로 다른 점수 수"], t), ""]

    t = []
    for it in items:
        row = [ko(it)]
        for m in (ma, mb):
            v = [m[(c, judge, it)] for c in origs if (c, judge, it) in m]
            row.append(f"{sum(v) / len(v):.2f}" if v else "-")
        t.append(row)
    out += ["■ 정상 대화의 항목별 평균", table(["항목", label_a, label_b], t), ""]

    t = []
    for lab, m in ((label_a, ma), (label_b, mb)):
        exp_d, oth_d, zero = [], [], 0
        for c in broken:
            base, kind = meta[c].get("base_id"), meta[c].get("perturbation")
            exp_items = EXPECTED_ITEMS.get(kind) or []
            for i in items:
                if (c, judge, i) in m and (base, judge, i) in m:
                    d = m[(c, judge, i)] - m[(base, judge, i)]
                    (exp_d if i in exp_items else oth_d).append(d)
        t.append([lab, f"{sum(exp_d) / len(exp_d):+.2f}" if exp_d else "-",
                  f"{sum(oth_d) / len(oth_d):+.2f}" if oth_d else "-",
                  f"{sum(1 for x in exp_d if x < 0)}/{len(exp_d)}" if exp_d else "-"])
    out += ["■ 망가진 대화(100%)의 점수 변화 (원본 대비)", table(["프롬프트", "기대 항목 평균", "나머지 항목 평균", "기대 항목 하락 건수"], t), ""]

    same = [(ma[k], mb[k]) for k in ma if k in mb]
    if same:
        e = sum(1 for x, y in same if abs(x - y) < 1e-9)
        out.append(f"■ 같은 칸의 점수 일치: {len(same)}건 중 {e}건({e / len(same):.0%}) 동일, 평균 차이({label_b}-{label_a}) "
                   f"{sum(y - x for x, y in same) / len(same):+.2f}점")
    return "\n".join(out) + "\n"


def _ranks(v: list[float]) -> list[float]:
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a: list[float], b: list[float]) -> float | None:
    """순위 상관. 한쪽이 상수(모두 같은 점수)이면 계산할 수 없어 None."""
    if len(a) < 3 or len(set(a)) < 2 or len(set(b)) < 2:
        return None
    ra, rb = _ranks(a), _ranks(b)
    ma, mb = st.mean(ra), st.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den


def rank_agreement(rows_a: list[dict], judge_a: str, rows_b: list[dict], judge_b: str) -> str:
    """정상 대화들을 두 judge가 비슷한 순서로 매기는지(항목별 순위 상관). 서로 독립적인 judge가 일치하면 점수 차이가 잡음이 아닐 가능성이 큼."""
    ma, mb = score_means([r for r in rows_a if r["judge"] == judge_a]), score_means([r for r in rows_b if r["judge"] == judge_b])
    meta = {r["conversation_id"]: r.get("meta", {}) for r in rows_a + rows_b}
    origs = sorted(c for c in {k[0] for k in ma} & {k[0] for k in mb}
                   if meta[c].get("perturbation") in (None, "", "original"))
    items = _items(rows_a + rows_b)
    t = []
    for it in items:
        xs = [ma[(c, judge_a, it)] for c in origs if (c, judge_a, it) in ma and (c, judge_b, it) in mb]
        ys = [mb[(c, judge_b, it)] for c in origs if (c, judge_a, it) in ma and (c, judge_b, it) in mb]
        r = spearman(xs, ys)
        t.append([ko(it), len(xs), f"{st.pstdev(xs):.2f}", f"{st.pstdev(ys):.2f}", "계산 불가(한쪽이 상수)" if r is None else f"{r:.2f}"])
    tot_a = [sum(ma[(c, judge_a, i)] for i in items if (c, judge_a, i) in ma) for c in origs]
    tot_b = [sum(mb[(c, judge_b, i)] for i in items if (c, judge_b, i) in mb) for c in origs]
    r = spearman(tot_a, tot_b)
    t.append(["대화별 합계", len(origs), f"{st.pstdev(tot_a):.2f}", f"{st.pstdev(tot_b):.2f}", "계산 불가" if r is None else f"{r:.2f}"])
    return "\n".join([f"■ 정상 대화 순위 일치: A={judge_a}, B={judge_b}",
                      table(["항목", "대화 수", "A 대화간 표준편차", "B 대화간 표준편차", "순위 상관(Spearman)"], t, right_from=1), ""])
