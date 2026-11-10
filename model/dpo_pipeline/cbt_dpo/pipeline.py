"""학습 전 자료 흐름. 선정·교체는 오프라인, Sol 호출은 별도 명시 실행이다."""
import copy
import json
from pathlib import Path
from . import common, generation, judge, preference


def read(path):
    return json.loads(Path(path).read_text())


def freeze_cohort(scores_path, output):
    """채점 완료6항목의 합계로 코호트를 먼저 고정한다. 이후 재채점으로 재선택하지 않는다."""
    grouped={}
    for line in Path(scores_path).read_text().splitlines():
        if not line.strip():continue
        row=json.loads(line)
        identifier=row['conversation_id'];item=row['item'];score=row['score']
        if item not in judge.ITEMS or type(score) is not int or not 0<=score<=6:
            raise ValueError('항목 또는 점수 오류')
        if row.get('parse_ok',True) is not True:raise ValueError('미파싱 점수')
        bucket=grouped.setdefault(identifier,{})
        if item in bucket:raise ValueError('중복 항목')
        bucket[item]=score
    if not grouped or any(set(rows)!=set(judge.ITEMS) for rows in grouped.values()):
        raise ValueError('모든 회기의6항목이 완료돼야 합니다.')
    import hashlib
    cohort={'score_file_sha256':hashlib.sha256(Path(scores_path).read_bytes()).hexdigest(),
            'threshold':'unrounded mean <=3.8','eligible_ids':sorted(
                identifier for identifier,rows in grouped.items() if sum(rows.values())*5<=19*6)}
    path=Path(output)
    if path.exists() and read(path)!=cohort:raise ValueError('고정 코호트 변경 금지')
    common.write_json(path,cohort)
    return cohort


def prepare_scenes(session, baseline_folder, instruction, cohort):
    identifier=session['conversation_id']
    if identifier not in cohort['eligible_ids']:return []
    pool={}
    for item in judge.ITEMS:
        row=read(baseline_folder/'results'/(item+'.json'))
        payload=judge.payload_for(session,item)
        if row['payload_sha256']!=common.digest(payload):raise ValueError('원회기 평가 맥락 불일치')
        judge.validate(row['result'],payload)
        for review in row['result']['turn_reviews']:
            if review['decision']=='needs_improvement':
                entry=pool.setdefault(review['turn_id'],{'flags':{},'language':set()})
                entry['flags'][item]={'score':row['score'],'review':review}
        for finding in row['result']['language_findings']:
            if finding['classification']=='problematic':
                entry=pool.setdefault(finding['turn_id'],{'flags':{},'language':set()})
                entry['flags'].setdefault(item,{'score':row['score'],'review':None})
                entry['language'].add(finding['quote'])
    scenes=[]
    for target,entry in sorted(pool.items()):
        primary=min(entry['flags'],key=lambda item:(entry['flags'][item]['score'],list(judge.ITEMS).index(item)))
        review=entry['flags'][primary]['review']
        reason=review['reason'] if review else 'CTRS 언어 관찰에서 설명 없는 혼입을 문제로 지적했다.'
        hint=review['rewrite_hint'] if review else '원래 상담 의미와 불확실성을 보존하고 혼입을 쉬운 한국어로 바꾼다.'
        if entry['language']:
            hint+='\nCTRS가 지적한 언어 구간을 자연스러운 한국어로 표현한다: '+json.dumps(sorted(entry['language']),ensure_ascii=False)
        scene=generation.build_scene(session,instruction,target,reason,hint)
        scene['ctrs_flag_provenance']={'primary_item':primary,'all_flagged_items':list(entry['flags'])}
        scenes.append(scene)
    return scenes


def pair_payload(scenes, candidates, orientation):
    entries=[]
    for scene in scenes:
        candidate=candidates[scene['scene_id']]['text']
        a,b=(scene['original'],candidate) if orientation==0 else (candidate,scene['original'])
        entries.append(dict(scene['context'],scene_id=scene['scene_id'],A=a,B=b))
    if entries:
        entries.append(dict(entries[0],scene_id='identity_control',A=scenes[0]['original'],B=scenes[0]['original']))
    payload={'rubric_definitions':{item:judge.definitions(item) for item in judge.ITEMS},'scenes':entries}
    payload['request_id']=common.digest(payload)[:16]
    return payload


def compare_candidates(folder,scenes):
    if not scenes:
        common.write_json(folder/'pair_outcomes.json',{})
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'preference_candidates.jsonl').write_text('')
        return []
    candidates={scene['scene_id']:read(folder/'candidates'/(scene['scene_id']+'.json')) for scene in scenes}
    batches=[]
    for orientation in range(2):
        payload=pair_payload(scenes,candidates,orientation)
        prompt=preference.PAIR_PROMPT+'\n비교 입력:\n'+json.dumps(payload,ensure_ascii=False)
        result=common.codex_roles.invoke(folder/'pairs','sol',prompt,preference.PAIR_SCHEMA)
        common.write_json(folder/'pairs/inputs'/f'order{orientation}.json',payload)
        common.write_json(folder/'pairs/raw_outputs'/f'order{orientation}.json',result)
        preference.validate_pairs(result,payload)
        common.write_json(folder/'pairs'/f'order{orientation}.json',result)
        batches.append(result)
    outcomes={}
    exports=[]
    for scene in scenes:
        reviews=[next(r for r in batch['reviews'] if r['scene_id']==scene['scene_id']) for batch in batches]
        outcome=preference.preference_outcome(reviews)
        outcomes[scene['scene_id']]=outcome
        if outcome in ['ctrs_content','content_and_language','language_repair']:
            exports.append({'prompt':scene['dpo_prompt'],'chosen':candidates[scene['scene_id']]['text'],
                'rejected':scene['original'],'metadata':{'source_session':scene['source_session'],
                'turn_id':scene['turn_id'],'preference_basis':outcome,'training_ready':False,
                'ctrs_flag_provenance':scene['ctrs_flag_provenance'],'individual_causal_effect_measured':False}})
    common.write_json(folder/'pair_outcomes.json',outcomes)
    (folder/'preference_candidates.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in exports))
    return exports


def edit_session(session, exports):
    modified=copy.deepcopy(session)
    targets=set()
    for row in exports:
        target=row['metadata']['turn_id']
        if row['metadata']['source_session']!=session['conversation_id'] or target in targets:
            raise ValueError('원회기 불일치 또는 중복 대상')
        if not 1<=target<=len(session['turns']) or session['turns'][target-1]['role']!='therapist':
            raise ValueError('잘못된 상담자 턴')
        if session['turns'][target-1]['text']!=row['rejected']:raise ValueError('원응답 불일치')
        targets.add(target)
        modified['turns'][target-1]['text']=row['chosen']
    changed={i+1 for i,(a,b) in enumerate(zip(session['turns'],modified['turns'],strict=True)) if a!=b}
    if changed!=targets:raise ValueError('허용된 수정 외 변경')
    modified['conversation_id']='SESSION_'+common.digest(modified['turns'])[:12]
    modified['meta']=dict(session.get('meta',{}),purpose='counterfactual_edit',evaluation_eligible=False)
    return modified
