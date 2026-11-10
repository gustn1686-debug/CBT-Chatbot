"""원래 시점의 이력과 CTRS 피드백으로 상담자 응답 하나를 생성한다."""
import json
from pathlib import Path
from . import common as shared
from . import judge

EDITOR_PROMPT='당신은 한국어 CBT 상담 응답을 교정하는 편집자다. 제공된 원응답을 개선해 같은 시점에서 사용할 대안 한 개를 쓴다.\n입력은 실제 상담자에게 주어진 지침·사전 맥락·과거 이력·원응답·잠정적인 수정 힌트다. 이후의 내담자 말은 없다.\n원응답을 그대로 복사하거나 어휘만 조금 바꾸지 말고, 실제 맥락에서 핵심 결함이 있는지 확인해 해결한다.\n힌트는 정답이 아니다. 실제 자료나 내담자의 요구와 어긋나는 힌트는 따르지 않는다. 원응답의 장점은 유지한다.\n상담 지침과 실제 사전 정보는 존중하되 계획을 수행·동의·변화의 증거로 바꾸지 않는다.\n확인되지 않은 사실·인과·결과를 확정하지 않고 내담자의 의미·시점·불확실성을 보존한다.\n현재 내담자가 묻거나 요청한 핵심에 직접 응답한다. 이미 답한 질문이나 거절한 제안을 반복하지 않는다.\n미래 반응·내담자의 다음 말·동의·수행을 만들지 않는다. 질문·공감·기법을 일률적으로 추가하지 않는다.\n한국어 존댓말의 실제 상담자 발화만 출력한다. 평가·수정 설명·제목·따옴표·점수·힌트 언급은 쓰지 않는다.\n'
GENERATION_WRAPPER='아래 메시지 배열의 system은 상담 응답 편집 지침, user는 실제 맥락과 원응답·잠정 안내다.\n지침에 따라 그 시점의 상담자 응답 하나만 새로 쓴다. 출력 JSON response에는 실제 한국어 상담 발화만 넣는다.\n평가·점수·수정 설명·인사 머리말을 덧붙이지 않는다. 도구를 사용하지 않는다.\n'
GENERATION_SCHEMA={'type': 'object', 'properties': {'response': {'type': 'string'}}, 'required': ['response'], 'additionalProperties': False}

def build_scene(session, counselor_instruction, turn_id, reason, hint):
    judge.payload_for(session,next(iter(judge.ITEMS)))
    if not isinstance(turn_id,int) or not 1<=turn_id<=len(session['turns']):
        raise ValueError('대상 턴 번호 오류')
    response=session['turns'][turn_id-1]
    if response['role']!='therapist':
        raise ValueError('상담자 응답만 수정할 수 있습니다.')
    history=shared.numbered_turns(session['turns'][:turn_id-1])
    if not history or history[-1]['role']!='client':
        raise ValueError('직전 내담자 발화가 필요합니다.')
    context={'counselor_instruction':counselor_instruction,
             'provided_context':session['provided_context'],'history':history}
    auxiliary={'original_response':response['text'],
               'revision_hint_unverified':hint,'possible_problem_unverified':reason}
    messages=[{'role':'system','content':EDITOR_PROMPT},
              {'role':'user','content':json.dumps(dict(context,**auxiliary),ensure_ascii=False)}]
    dpo_prompt=[{'role':'system','content':counselor_instruction.strip()+'\n\n'+session['provided_context']}]
    dpo_prompt += [{'role':'user' if row['role']=='client' else 'assistant','content':row['text']} for row in history]
    return {'scene_id':shared.digest(context)[:12],'source_session':session['conversation_id'],
            'turn_id':turn_id,'context':context,'original':response['text'],
            'generation_auxiliary':auxiliary,'generation_messages':messages,'dpo_prompt':dpo_prompt}


def validate_scene(scene):
    context=scene['context']
    history=context['history']
    if [row['turn_id'] for row in history]!=list(range(1,scene['turn_id'])):
        raise ValueError('이력이 대상 턴 직전까지의 연속 번호가 아닙니다.')
    session={'conversation_id':scene['source_session'],'provided_context':context['provided_context'],
             'turns':[{'role':row['role'],'text':row['text']} for row in history]+
                     [{'role':'therapist','text':scene['original']}]}
    auxiliary=scene['generation_auxiliary']
    expected=build_scene(session,context['counselor_instruction'],scene['turn_id'],
                         auxiliary['possible_problem_unverified'],auxiliary['revision_hint_unverified'])
    for key in expected:
        if scene[key]!=expected[key]:raise ValueError('표준 생성 맥락 또는 DPO prompt가 변경됐습니다.')


def generate_one(folder,scene):
    validate_scene(scene)
    prompt=GENERATION_WRAPPER+'\n'+json.dumps(scene['generation_messages'],ensure_ascii=False)
    request_hash=shared.digest({'prompt':prompt,'schema':GENERATION_SCHEMA})
    path=folder/'candidates'/(scene['scene_id']+'.json')
    if path.exists():
        row=json.loads(path.read_text())
        if row['request_hash']!=request_hash:raise ValueError('저장된 생성 입력 변경')
        return row
    output=shared.codex_roles.invoke(folder/'generator','teacher',prompt,GENERATION_SCHEMA)
    shared.write_json(folder/'raw_outputs'/(scene['scene_id']+'.json'),output)
    text=output['response'].strip()
    if not text or len(text)>2000:raise ValueError('빈 응답 또는2000자 초과. 자동 재작성하지 않습니다.')
    row={'text':text,'request_hash':request_hash,'training_ready':False}
    shared.write_json(path,row)
    return row
