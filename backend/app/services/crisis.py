"""위기 감지: 키워드 매칭. 감지되면 LLM을 호출하지 않고 고정 안내 문구를 내려준다.

키워드 목록과 문구/연락처는 임시안이며, 팀 합의(docs/api-spec.md §7-4) 후 교체한다.
"""

import re

CRISIS_KEYWORDS = (
    "죽고 싶",
    "죽고싶",
    "자살",
    "자해",
    "목숨을 끊",
    "스스로 목숨",
    "사라지고 싶",
    "사라져버리고 싶",
    "살기 싫",
    "살고 싶지 않",
    "죽어버리",
    "극단적인 선택",
    "극단적 선택",
)

# 띄어쓰기 차이("죽고  싶")를 흡수하기 위해 공백을 제거한 뒤 비교한다.
_NORMALIZED = tuple(re.sub(r"\s+", "", k) for k in CRISIS_KEYWORDS)

CRISIS_RESOURCES = [
    {"name": "자살예방 상담전화", "tel": "109"},
    {"name": "정신건강 위기상담전화", "tel": "1577-0199"},
]

# 프론트가 위기 시트(전화 연결 카드)를 따로 띄우므로 말풍선에는 짧은 한 문단만 둔다.
# 시트를 닫은 뒤에도 대화 기록에 연락처가 남도록 핵심 번호 하나는 포함한다.
CRISIS_MESSAGE = (
    "지금 많이 힘드신 것 같아요. 혼자 견디지 않으셔도 괜찮아요. "
    "자살예방 상담전화 109(24시간)로 바로 연락해 보실 수 있어요."
)


def detect_crisis(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    return any(k in compact for k in _NORMALIZED)
