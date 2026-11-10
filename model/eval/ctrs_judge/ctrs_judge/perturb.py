"""망가뜨린 대화(perturbation) 생성. 각 유형은 CTRS 한 항목의 점수 하락을 기대하고 만듦.

규칙 기반(API 불필요): repeat, no_empathy
템플릿(API 불필요, 기본): lecture, directive, offtopic
LLM 재작성(선택, API 필요): lecture, directive, offtopic에 complete 함수를 넘기면 사용
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

PROMPT_DIR = Path(__file__).resolve().parent.parent / "perturb_prompts"

# 유형 -> 점수 하락을 기대하는 항목(앞이 주 항목). 공감 제거는 반영 문장도 함께 지워서 이해도 포함함
EXPECTED_ITEMS = {
    "repeat": ["general_1_understanding"],
    "no_empathy": ["general_2_interpersonal_effectiveness", "general_1_understanding"],
    "directive": ["general_3_collaboration"],
    "lecture": ["CBT_1_guided_discovery"],
    "offtopic": ["CBT_2_focus"],
    "cold": ["general_2_interpersonal_effectiveness"],
}
EXPECTED_DROP = {k: v[0] for k, v in EXPECTED_ITEMS.items()}
SEVERITIES = (30, 60, 100)
RULE_BASED = ("repeat", "no_empathy", "cold")
LLM_BASED = ("lecture", "directive", "offtopic")

_SENT_SPLIT = re.compile(r"(?<=[.?!])\s+")


def _therapist_idx(turns: list[dict]) -> list[int]:
    return [i for i, t in enumerate(turns) if t["role"] == "therapist"]


def repeat(turns: list[dict]) -> list[dict]:
    """세 번째 상담자 발화부터 두 번째 상담자 발화(첫 탐색 질문)를 그대로 반복함."""
    idx = _therapist_idx(turns)
    if len(idx) < 3:
        raise ValueError("상담자 발화가 3개 미만")
    anchor = turns[idx[1]]["text"]
    out = [dict(t) for t in turns]
    for i in idx[2:]:
        out[i]["text"] = anchor
    return out


def no_empathy(turns: list[dict]) -> list[dict]:
    """첫 인사를 제외하고 상담자 발화에서 마지막 문장만 남겨 공감, 반영 문장을 제거함."""
    idx = _therapist_idx(turns)
    out = [dict(t) for t in turns]
    for i in idx[1:]:
        sentences = _SENT_SPLIT.split(out[i]["text"].strip())
        out[i]["text"] = sentences[-1]
    return out

# API 없이 만드는 템플릿 문장 풀. 내담자 말과 무관하게 해당 결함을 드러내도록 일부러 거칠게 만든 것임.
# 연속 반복이 반복 결함(repeat)과 섞이지 않도록 대화의 상담자 발화 수보다 넉넉히 둠.
TEMPLATES = {
    "lecture": [
        "그렇게 생각하시는 건 사실과 다릅니다. 객관적으로 보면 명백한 과장이에요.",
        "제가 보기에 그건 잘못된 생각이에요. 그런 식으로 생각하시면 안 됩니다.",
        "다들 그렇게 느끼는 건 아니에요. 이제는 생각을 바꾸셔야 합니다.",
        "그건 논리적이지 않아요. 제 말이 맞으니 그렇게 받아들이시는 게 좋겠습니다.",
        "솔직히 말씀드리면 그건 비합리적인 사고입니다. 긍정적으로 보셔야 해요.",
        "그런 걱정은 전혀 근거가 없어요. 제가 장담하는데 그렇게 되지 않습니다.",
        "이미 답은 나와 있어요. 그렇게 부정적으로만 보시는 게 문제의 원인입니다.",
        "그렇게 말씀하시지만 사실은 그 반대예요. 제 설명을 잘 들어보세요.",
        "그건 인지 오류예요. 그러니 지금 하시는 생각은 틀렸다고 인정하셔야 합니다.",
        "생각을 고치지 않으면 계속 힘들 수밖에 없어요. 제 방식대로 보시는 게 맞습니다.",
        "그건 변명처럼 들려요. 현실을 직시하고 받아들이셔야 합니다.",
        "아무리 생각해도 그런 해석은 설득력이 없어요. 제 관점이 더 정확합니다.",
        "그렇게 생각하는 사람은 거의 없어요. 지금의 생각은 바로잡아야 합니다.",
        "제가 여러 번 말씀드렸듯이 그건 사실이 아니에요. 이제 그만 인정하세요.",
        "결론부터 말씀드리면 문제는 생각 방식이에요. 제 말대로 바꾸시면 됩니다.",
        "그런 식의 판단은 옳지 않습니다. 반박하실 여지가 없어요.",
        "더 따져볼 필요도 없어요. 그건 틀린 생각이니 버리시는 게 맞습니다.",
    ],
    "directive": [
        "다음 주까지 매일 30분씩 산책하세요. 이건 꼭 하셔야 합니다.",
        "목표는 제가 정했어요. 시키는 대로 따라오시면 됩니다.",
        "오늘부터 하루에 세 번 기록하세요. 방법은 제가 알려드린 대로만 하세요.",
        "계획은 이미 다 짜 두었습니다. 의견은 필요 없고 그대로 실행하세요.",
        "이번 주에는 사람들과의 약속을 모두 취소하고 휴식하세요.",
        "제가 말한 순서대로 진행하세요. 다른 방법은 생각하지 마세요.",
        "내일부터 아침 일곱 시에 일어나세요. 예외는 없습니다.",
        "과제는 이겁니다. 매일 저녁 오늘 한 일을 열 줄씩 적어 오세요.",
        "그 문제는 이렇게 처리하세요. 선택할 필요 없이 이 방법이 정답입니다.",
        "다음 상담 전까지 이 목록을 전부 해 오세요. 빠뜨리면 안 됩니다.",
        "지금 바로 그 사람에게 연락하세요. 제가 시키는 대로 하시면 됩니다.",
        "앞으로 상담 목표는 제가 정하는 대로 갑니다. 따라오세요.",
        "하루에 한 번씩 거울을 보고 제가 드린 문장을 읽으세요. 반드시 하셔야 합니다.",
        "더 생각하지 말고 제 지시를 따르세요. 그게 가장 빠릅니다.",
        "이번 주부터 이 규칙을 지키세요. 어기면 효과가 없습니다.",
        "스스로 정하려고 하지 마세요. 제가 정한 방법대로만 하세요.",
        "마지막으로 말씀드립니다. 제가 드린 숙제를 빠짐없이 해 오세요.",
    ],
    "offtopic": [
        "그렇군요. 그런데 요즘 날씨가 참 좋죠? 주말에 어디 다녀오셨어요?",
        "아, 네네. 근데 점심은 드셨어요? 저는 새로 생긴 국숫집이 맛있더라고요.",
        "그렇죠. 참, 최근에 보신 드라마 있어요? 요즘 재밌는 게 많더라고요.",
        "아하. 그런데 혹시 반려동물 키우세요? 저는 강아지가 너무 귀여워서요.",
        "네, 그렇군요. 그건 그렇고 휴가 때 가보고 싶은 여행지가 있으세요?",
        "음, 그래요. 요즘 커피 어디서 드세요? 저는 원두에 꽤 까다롭거든요.",
        "그러시군요. 참, 좋아하는 음악 장르가 뭐예요? 저는 재즈를 자주 들어요.",
        "맞아요. 근데 운동은 좋아하세요? 요즘 러닝이 유행이라고 하더라고요.",
        "아, 그래요. 그런데 어릴 때 살던 동네는 어땠어요? 저는 시골이었어요.",
        "네네. 이번 주말에 비 온다던데 우산 챙기셨어요?",
        "그렇군요. 혹시 요리 좋아하세요? 요즘 집밥 레시피를 찾아보고 있어서요.",
        "아, 그렇네요. 그런데 스마트폰은 어떤 걸 쓰세요? 새 모델이 나왔더라고요.",
        "네. 참, 좋아하는 계절이 있으세요? 저는 가을이 제일 좋아요.",
        "그래요. 근데 영화 좋아하세요? 요즘 개봉작 중에 볼 만한 게 있대요.",
        "음, 그렇군요. 아침형이세요, 저녁형이세요? 저는 완전 올빼미예요.",
        "아하. 그런데 책 읽는 거 좋아하세요? 요즘 베스트셀러가 궁금해서요.",
        "그렇군요. 오늘 오시는 길에 차가 많이 막혔나요?",
    ],
}


def _template_rewrite(turns: list[dict], kind: str) -> list[dict]:
    idx = _therapist_idx(turns)
    pool = TEMPLATES[kind]
    out = [dict(t) for t in turns]
    for n, i in enumerate(idx[1:]):  # 첫 인사 유지
        out[i]["text"] = pool[n % len(pool)]
    return out


# 차가운 태도: no_empathy(공감 문장 제거)에 눈에 띄게 무뚝뚝하고 성의 없는 말투를 더한 버전.
# 욕설이나 모욕은 넣지 않고 말투의 따뜻함만 낮춤. 질문 내용은 no_empathy와 동일해서 차이가 말투에서만 생김.
COLD_PREFIXES = [
    "네.", "그건 중요하지 않아요.", "시간이 없으니 넘어가죠.", "그건 알겠고요.", "그런 얘기는 넘어가겠습니다.",
    "누구나 겪는 일이에요.", "그렇군요. 다음으로 가죠.", "빨리 진행할게요.", "그 부분은 됐고요.",
    "일단 다음 질문입니다.", "그건 별로 도움이 안 되고요.", "알겠습니다. 계속하죠.", "네, 그다음은요.",
    "그건 크게 중요하지 않습니다.", "길게 말씀하실 필요는 없고요.", "그 얘긴 그만하고요.", "좋아요. 본론으로 가죠.",
]


def cold(turns: list[dict]) -> list[dict]:
    """첫 인사를 제외한 상담자 발화를 '무뚝뚝한 한마디 + 마지막 문장(질문)'으로 바꿈."""
    idx = _therapist_idx(turns)
    out = [dict(t) for t in turns]
    for n, i in enumerate(idx[1:]):
        last = _SENT_SPLIT.split(out[i]["text"].strip())[-1]
        out[i]["text"] = f"{COLD_PREFIXES[n % len(COLD_PREFIXES)]} {last}"
    return out


def parse_rewrite_output(text: str, n_expected: int) -> list[str]:
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    arr = json.loads(s)
    if not isinstance(arr, list) or not all(isinstance(x, str) and x.strip() for x in arr):
        raise ValueError("문자열 배열이 아님")
    if len(arr) != n_expected:
        raise ValueError(f"상담자 발화 수 불일치: {len(arr)} != {n_expected}")
    return arr


def llm_rewrite(turns: list[dict], kind: str, complete: Callable[[str], str], attempts: int = 3) -> list[dict]:
    idx = _therapist_idx(turns)
    template = (PROMPT_DIR / "common.txt").read_text(encoding="utf-8")
    instruction = (PROMPT_DIR / f"{kind}.txt").read_text(encoding="utf-8").strip()
    dialogue = "\n".join(
        f"{'상담자' if t['role'] == 'therapist' else '내담자'}: {t['text']}" for t in turns)
    prompt = (template.replace("{n_therapist}", str(len(idx)))
              .replace("{instruction}", instruction).replace("{dialogue}", dialogue))
    last: Exception | None = None
    for _ in range(attempts):
        try:
            new = parse_rewrite_output(complete(prompt), len(idx))
            break
        except (ValueError, json.JSONDecodeError) as e:
            last = e
    else:
        raise RuntimeError(f"{kind} 재작성 실패: {last}")
    out = [dict(t) for t in turns]
    for i, text in zip(idx, new):
        out[i]["text"] = text.strip()
    out[idx[0]]["text"] = turns[idx[0]]["text"]  # 인사는 원문 유지
    return out


def _blend(orig: list[dict], full: list[dict], frac: float) -> list[dict]:
    """100% 변형(full) 중 실제로 바뀐 상담자 발화의 frac만 적용함. 대화 전체에 고르게 퍼지게 결정적으로 고름."""
    cand = [i for i, (o, f) in enumerate(zip(orig, full)) if o["role"] == "therapist" and o["text"] != f["text"]]
    k = min(len(cand), max(1, round(frac * len(cand)))) if cand else 0
    chosen = {cand[int((j + 0.5) * len(cand) / k)] for j in range(k)}
    return [dict(f) if i in chosen else dict(o) for i, (o, f) in enumerate(zip(orig, full))]


def make_variant(base: dict, kind: str, complete: Callable[[str], str] | None = None, severity: int = 100) -> dict:
    if kind in RULE_BASED:
        turns = {"repeat": repeat, "no_empathy": no_empathy, "cold": cold}[kind](base["turns"])
    elif kind in LLM_BASED:
        turns = (llm_rewrite(base["turns"], kind, complete) if complete
                 else _template_rewrite(base["turns"], kind))
    else:
        raise ValueError(f"알 수 없는 유형: {kind}")
    if not 0 < severity <= 100:
        raise ValueError("severity는 1~100")
    if severity < 100:
        turns = _blend(base["turns"], turns, severity / 100)
    meta = {**base.get("meta", {}), "perturbation": kind, "base_id": base["conversation_id"],
            "expected_drop": EXPECTED_DROP[kind], "severity": severity}
    suffix = "" if severity == 100 else f"_p{severity}"  # 100%의 id는 기존과 동일하게 유지
    return {"conversation_id": f"{base['conversation_id']}__{kind}{suffix}", "turns": turns, "meta": meta}


def as_original(base: dict) -> dict:
    return {**base, "meta": {**base.get("meta", {}), "perturbation": "original", "base_id": base["conversation_id"]}}
