"""실제 Sol A/B 프롬프트·스키마·양순서 채택 규칙."""
from . import common as shared
PAIR_PROMPT='CTRS 기준을 적용하는 한국어 상담 응답 비교다. 도구를 사용하지 않는다.\n각 장면은 같은 과거 맥락과 현재 A/B 응답이다. 작성자·원본 여부·기존 점수·진단·미래 대화는 없다.\n전달된 원 CTRS 기준은 회기 척도다. 턴별 숫자 점수로 바꾸거나 모든 응답에 모든 기법을 요구하지 않는다.\n현재 내담자 요청에 필요한 작업에 한해 관련 기준을 적용한다. 여섯 기준 중 현재 요청에 필요한 작업을 살핀다. 특정 기법을 모든 턴에 요구하지 않는다.\nA/B 각각 appropriate/needs_improvement/insufficient_context로 판정하고 근거를 직접 인용한다.\n한 응답이 적절하고 다른 응답에 실질적인 결함이 있을 때만 A/B 우세를 고른다.\n둘 다 적절하면 tie, 둘 다 부족하면 both_inadequate, 판단 맥락이 부족하면 insufficient_context다.\n같은 텍스트끼리는 A/B 우세를 만들지 않는다. 문체·질문 유무·길이만으로 우열을 만들지 않는다.\n미확인 사실·인과·의향을 성과로 바꾸는 표현이나 내담자 요구·속도 무시는 장점과 함께 확인한다.\n프로필 사실은 대화에서 미언급이라는 이유로 날조로 판단하지 않는다. 사전 계획은 수행의 증거가 아니다.\n각각의 언어 품질은 A_language/B_language에서 별도로 판단한다. 언어 문제만으로 상담 내용 우세를 만들지 않는다.\n언어 판단은 acceptable/needs_revision/uncertain이다. 문제면 실제 구간을 인용한다. 통용 용어·인용·설명된 병기는 자동 오류가 아니다.\nevidence.source는 A/B/history/provided_context다. A/B/provided_context의 turn_id는0, history는 입력 원번호다.\n우세 판정이면 A/B를 각각 직접 인용하여 차이를 설명한다. 한국어로 짧은 최종 근거만 출력한다.\n'
PAIR_SCHEMA={'type': 'object', 'properties': {'request_id': {'type': 'string'}, 'reviews': {'type': 'array', 'items': {'type': 'object', 'properties': {'scene_id': {'type': 'string'}, 'verdict': {'type': 'string', 'enum': ['A', 'B', 'tie', 'both_inadequate', 'insufficient_context']}, 'A_decision': {'type': 'string', 'enum': ['appropriate', 'needs_improvement', 'insufficient_context']}, 'B_decision': {'type': 'string', 'enum': ['appropriate', 'needs_improvement', 'insufficient_context']}, 'reason': {'type': 'string'}, 'A_language': {'type': 'object', 'properties': {'decision': {'type': 'string', 'enum': ['acceptable', 'needs_revision', 'uncertain']}, 'quotes': {'type': 'array', 'items': {'type': 'string'}}, 'reason': {'type': 'string'}}, 'required': ['decision', 'quotes', 'reason'], 'additionalProperties': False}, 'B_language': {'type': 'object', 'properties': {'decision': {'type': 'string', 'enum': ['acceptable', 'needs_revision', 'uncertain']}, 'quotes': {'type': 'array', 'items': {'type': 'string'}}, 'reason': {'type': 'string'}}, 'required': ['decision', 'quotes', 'reason'], 'additionalProperties': False}, 'evidence': {'type': 'array', 'items': {'type': 'object', 'properties': {'source': {'type': 'string', 'enum': ['A', 'B', 'history', 'provided_context']}, 'turn_id': {'type': 'integer'}, 'quote': {'type': 'string'}}, 'required': ['source', 'turn_id', 'quote'], 'additionalProperties': False}}}, 'required': ['scene_id', 'verdict', 'A_decision', 'B_decision', 'reason', 'A_language', 'B_language', 'evidence'], 'additionalProperties': False}}}, 'required': ['request_id', 'reviews'], 'additionalProperties': False}

def validate_pairs(result, payload):
    if result['request_id'] != payload['request_id']:
        raise ValueError('비교 요청 불일치')
    expected = {scene['scene_id']: scene for scene in payload['scenes']}
    if sorted(row['scene_id'] for row in result['reviews']) != sorted(expected):
        raise ValueError('장면 누락 또는 중복')
    for review in result['reviews']:
        scene = expected[review['scene_id']]
        a, b, verdict = review['A_decision'], review['B_decision'], review['verdict']
        valid = {'A': a=='appropriate' and b=='needs_improvement',
            'B': b=='appropriate' and a=='needs_improvement',
            'tie': a==b=='appropriate', 'both_inadequate': a==b=='needs_improvement',
            'insufficient_context': 'insufficient_context' in [a,b]}
        if not valid.get(verdict) or (scene['A']==scene['B'] and verdict in ['A','B']):
            raise ValueError('선호·개별 판정 또는 동일 응답 대조 불일치')
        for evidence in review['evidence']:
            origin=evidence['source']
            if origin == 'history':
                source=next((row['text'] for row in scene['history'] if row['turn_id']==evidence['turn_id']),None)
            else:
                if evidence['turn_id'] != 0:
                    raise ValueError('A/B·사전 맥락의 인용 번호 오류')
                source=scene.get(origin)
            if source is None:
                raise ValueError('현재 맥락 밖 인용')
            shared.check_quote(evidence['quote'], source)
        if verdict in ['A','B'] and not {'A','B'} <= {e['source'] for e in review['evidence']}:
            raise ValueError('우열 직접 인용 부족')
        for label in ['A','B']:
            finding = review[label+'_language']
            if finding['decision'] != 'acceptable' and not finding['quotes']:
                raise ValueError('언어 문제 인용 없음')
            for quote in finding['quotes']:
                shared.check_quote(quote, scene[label])

def preference_outcome(reviews):
    """내용 우세와 언어만의 수정을 분리한다. 둘 다 부족한 답을 채택하지 않는다."""
    choices=[];candidate_ok=[];original_bad_language=[];original_uncertain=[]
    for orientation,row in enumerate(reviews):
        candidate='B' if orientation==0 else 'A';original='A' if orientation==0 else 'B'
        choices.append('candidate' if row['verdict']==candidate else 'original' if row['verdict']==original else row['verdict'])
        candidate_ok.append(row[candidate+'_decision']=='appropriate' and row[candidate+'_language']['decision']=='acceptable')
        original_bad_language.append(row[original+'_language']['decision']=='needs_revision')
        original_uncertain.append(row[original+'_decision']=='insufficient_context' or row[original+'_language']['decision']=='uncertain')
    if len(reviews)!=2 or not all(candidate_ok) or any(original_uncertain):return 'hold'
    if choices==['candidate','candidate']:
        return 'content_and_language' if all(original_bad_language) else 'ctrs_content'
    if all(original_bad_language) and all(choice in ['candidate','tie'] for choice in choices):return 'language_repair'
    return 'not_preferred' if choices[0]==choices[1] else 'order_unstable'
