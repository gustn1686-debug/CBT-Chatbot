"""위기어 감지 키워드 테스트. 문장은 설명용으로 만든 예시다 (docs/crisis-keywords-draft.md)."""

import pytest

from app.services.crisis import KEYWORD_VERSION, detect_crisis

# 기존 + A~D 유형에서 감지해야 하는 문장
SHOULD_DETECT = [
    # 기존
    "죽고 싶어요",
    "죽고싶다",
    "죽 고 싶 어",
    "자살 생각이 나요",
    "자해했어요",
    "살기 싫어요",
    "오늘 밤에 사라지고 싶어요",
    "극단적인 선택",
    # A. 죽음 의사
    "그냥 죽을까 생각 중이에요",
    "죽어버릴까",
    "이제 죽을래",
    "죽으려고 했어요",
    "죽고시퍼",
    # B. 방법·준비
    "뛰어내리고 싶다는 생각이 들어요",
    "유서를 써 놨어요",
    "목을 매고 싶어요",
    "약을 다 먹어버릴까 봐요",
    "손목을 긋고 싶어요",
    # C. 소극적
    "내가 없어졌으면 좋겠어",
    "태어나지 말걸 그랬어",
    "아침에 눈을 뜨지 않았으면 좋겠어요",
    # D. 삶의 포기
    "다 끝내고 싶어요",
    "더 이상 못 살겠어요",
    "살 이유가 없는 것 같아요",
    "사는 의미를 모르겠어요",
    "모든 걸 끝내고 싶어",
]

# 감지되면 안 되는 일상 표현
SHOULD_NOT_DETECT = [
    "웃겨 죽겠다",
    "배고파 죽겠어",
    "피곤해 죽겠어요",
    "시험이 끝나서 너무 좋아요",
    "숙제를 빨리 끝내고 싶어요",
    "더 이상 못 참겠어요",
    "그 일은 끝내고 싶어요",
    "친구가 번지점프에서 뛰어내렸어요",
    "사는 게 힘들어요",
    "일이 너무 많아서 죽을 것 같아요",
    "오늘 너무 창피해서 쥐구멍에 숨고 싶어요",
    "살이 쪄서 고민이에요",
    "태어난 날이 내일이에요",
    "약을 먹었는데 졸려요",
    "발표가 끝나서 후련해요",
    "잠을 못 자서 눈을 뜨기가 힘들어요",
    "없어진 지갑을 찾고 싶어요",
]


@pytest.mark.parametrize("text", SHOULD_DETECT)
def test_detects_crisis(text):
    assert detect_crisis(text), text


@pytest.mark.parametrize("text", SHOULD_NOT_DETECT)
def test_ignores_everyday_expressions(text):
    assert not detect_crisis(text), text


# 오탐이 나더라도 놓치는 것보다 낫다고 정한 표현. (사용자가 시트에서 일반 대화로 돌아갈 수 있다)
ACCEPTED_FALSE_POSITIVES = [
    "유서 깊은 건물이에요",
    "자살 예방 뉴스를 봤어요",
]


@pytest.mark.parametrize("text", ACCEPTED_FALSE_POSITIVES)
def test_accepted_false_positives_are_detected(text):
    assert detect_crisis(text), text


def test_known_gaps_are_documented():
    """키워드 방식으로 못 잡는 표현. 감지되기 시작하면 문서(docs/crisis-keywords-draft.md)도 갱신한다.

    - 돌려 말하는 표현
    - E 유형(영어·변형 표기)은 이번에 넣지 않았다
    """
    for text in ["아침에 눈을 안 뜨고 싶어요", "I want to die", "kill myself", "ㅈㅅ하고싶어"]:
        assert not detect_crisis(text), text


def test_keyword_version_bumped():
    assert KEYWORD_VERSION == "v2"
