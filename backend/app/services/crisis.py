"""위기 감지: 키워드 매칭. 감지되면 LLM을 호출하지 않고 고정 안내 문구를 내려준다.

키워드 목록과 문구/연락처는 임시안이며, 팀·전문가 검토 후 교체한다. (docs/api-spec.md §7-4, docs/crisis-keywords-draft.md)
"""

import hashlib
import hmac
import re

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import CrisisEvent, User

# 키워드는 docs/crisis-keywords-draft.md 의 A~D 유형까지 포함한다. (E. 영어·변형 표기는 제외)
# 정책: 놓치는 것보다 오탐이 낫다. 오탐이면 사용자가 위기 안내 시트에서 "일반 대화로 돌아가기"를 고를 수 있다.
# 다만 오탐이면 그 메시지는 모델로 가지 않으므로, 일상에서 아주 흔한 표현("~해서 죽겠다")은 넣지 않는다.
CRISIS_KEYWORDS = (
    # 기존: 자살·자해·죽음 의사
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
    # A. 죽음 의사 (직접)
    "죽을까",
    "죽을래",
    "죽어버릴",
    "죽고 말",
    "죽으려",
    "죽어야겠",
    "죽고시퍼",
    "뒤지고싶",
    "디지고싶",
    # B. 방법·준비 언급
    "뛰어내리",
    "투신",
    "목을 매",
    "목매",
    "손목을 긋",
    "손목 긋",
    "약을 다 먹",
    "약 다 먹",
    "과다복용",
    "번개탄",
    "유서",
    # C. 사라지고 싶다 (소극적)
    "없어지고 싶",
    "없어졌으면",
    "사라졌으면",
    "눈을 뜨지 않",
    "눈 뜨고 싶지 않",
    "깨어나지 않",
    "태어나지 말",
    "태어나지 않았",
    # D. 삶의 포기·무의미
    "못 살겠",
    "더는 못 살",
    "살 이유",
    "살아갈 이유",
    "사는 의미",
    "사는 게 의미",
    "다 끝내고 싶",
    "모든 걸 끝내",
    "삶을 끝내",
    "생을 마감",
)

# 띄어쓰기 차이("죽고  싶")를 흡수하기 위해 공백을 제거한 뒤 비교한다.
_NORMALIZED = tuple(re.sub(r"\s+", "", k) for k in CRISIS_KEYWORDS)

CRISIS_CATEGORY = "self_harm"
KEYWORD_VERSION = "v2"  # 키워드 목록을 바꾸면 올린다 (필터 개선 추적용)

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


def anon_code(user_id: str) -> str:
    """되돌릴 수 없는 가명 코드. 비밀키가 바뀌면 이전 코드와 이어지지 않는다."""
    key = get_settings().crisis_log_secret.encode()
    return hmac.new(key, user_id.encode(), hashlib.sha256).hexdigest()[:16]


def log_crisis_event(db: Session, user: User) -> None:
    """통계용 비식별 기록. 사용자/대화 ID, 메시지 내용, 키워드 원문은 저장하지 않는다."""
    db.add(
        CrisisEvent(
            anon_code=anon_code(user.id),
            category=CRISIS_CATEGORY,
            keyword_version=KEYWORD_VERSION,
            user_kind="guest" if user.is_guest else "member",
        )
    )
