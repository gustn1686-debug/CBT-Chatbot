import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from cbt_dpo import common, generation, judge, pipeline, preference


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.session={'conversation_id':'synthetic','provided_context':'새 합성 형식 자료',
                      'turns':[{'role':'client','text':'발표가 걱정돼요.'},{'role':'therapist','text':'그 걱정이 드는 순간을 살펴볼까요?'}]}
        self.session['provided_context']='새 합성 예시: 발표를 걱정함.'

    def test_prompt_files_and_schemas_match_runtime(self):
        p=Path(__file__).resolve().parents[1]/'prompts'
        for name,text in [('ctrs_addendum.txt',judge.ADDENDUM),('ctrs_instructions.txt',judge.INSTRUCTIONS),
                          ('editor_system.txt',generation.EDITOR_PROMPT),('editor_wrapper.txt',generation.GENERATION_WRAPPER),
                          ('preference_system.txt',preference.PAIR_PROMPT)]:
            self.assertEqual((p/name).read_text(),text)
        for name,schema in [('ctrs_output',judge.SCHEMA),('generation_output',generation.GENERATION_SCHEMA),('preference_output',preference.PAIR_SCHEMA)]:
            self.assertEqual(json.loads((p/(name+'.schema.json')).read_text()),schema)
        self.assertEqual({k:judge.prepare_hash(k) for k in judge.ITEMS},json.loads((p.parent/'cbt_dpo/rubric_hashes.json').read_text())['prompt_hashes'])

    def test_generation_uses_prefix_and_dpo_prompt_excludes_hint(self):
        session=copy.deepcopy(self.session)
        session['turns'].append({'role':'client','text':'아직 말하지 않은 미래 내용'})
        scene=generation.build_scene(session,'상담 지침',2,'문제 가설','수정 전용 비밀 힌트')
        generation.validate_scene(scene)
        self.assertNotIn('미래 내용',json.dumps(scene,ensure_ascii=False))
        self.assertNotIn('비밀 힌트',json.dumps(scene['dpo_prompt'],ensure_ascii=False))
        scene['generation_messages'][0]['content']='변조된 지침'
        with self.assertRaises(ValueError):generation.validate_scene(scene)

    def test_all_four_flagged_turns_included_no_fixed_cap(self):
        session=copy.deepcopy(self.session)
        session['turns']=session['turns']*4
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            for item in judge.ITEMS:
                payload=judge.payload_for(session,item)
                result={'request_id':payload['request_id'],'item':item,'raw_response':'3, 합성 검사 설명.',
                        'language_findings':[],'session_limits':[],'limitations':'모의 검사',
                        'turn_reviews':[{'turn_id':i,'decision':'needs_improvement','reason':'수정 근거',
                            'rewrite_hint':'시점 제한 수정 방향','criterion_quote':judge.definitions(item).splitlines()[0],
                            'evidence':[{'turn_id':i,'quote':session['turns'][i-1]['text']}]} for i in [2,4,6,8]]}
                common.write_json(folder/'results'/(item+'.json'),{'score':3,'result':result,'payload_sha256':common.digest(payload)})
            scenes=pipeline.prepare_scenes(session,folder,'상담 지침',{'eligible_ids':['synthetic']})
            self.assertEqual([s['turn_id'] for s in scenes],[2,4,6,8])
            for s in scenes:generation.validate_scene(s)

    def test_cohort_uses_complete_unrounded_scores_and_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);source=folder/'scores.jsonl';output=folder/'cohort.json'
            rows=[{'conversation_id':'a','item':item,'score':score} for item,score in zip(judge.ITEMS,[4,4,4,4,3,3])]
            source.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            self.assertEqual(pipeline.freeze_cohort(source,output)['eligible_ids'],['a'])
            rows[-1]['score']=4
            source.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            with self.assertRaises(ValueError):pipeline.freeze_cohort(source,output)

    def test_stable_preference_and_language_only_repair(self):
        rows=[]
        for candidate,original in [('B','A'),('A','B')]:
            rows.append({'verdict':candidate,candidate+'_decision':'appropriate',original+'_decision':'needs_improvement',
                         candidate+'_language':{'decision':'acceptable'},original+'_language':{'decision':'acceptable'}})
        self.assertEqual(preference.preference_outcome(rows),'ctrs_content')
        rows[1]['verdict']='tie'
        self.assertEqual(preference.preference_outcome(rows),'order_unstable')
        rows[0]['A_language']['decision']='needs_revision'
        rows[1]['B_language']['decision']='needs_revision'
        self.assertEqual(preference.preference_outcome(rows),'language_repair')

    def test_edit_only_changes_accepted_therapist_turn(self):
        export={'rejected':self.session['turns'][1]['text'],'chosen':'새 대안',
                'metadata':{'source_session':'synthetic','turn_id':2}}
        edited=pipeline.edit_session(self.session,[export])
        self.assertEqual(edited['turns'][0],self.session['turns'][0])
        self.assertEqual(edited['provided_context'],self.session['provided_context'])
        self.assertEqual(edited['turns'][1]['text'],'새 대안')
        self.assertEqual(self.session['turns'][1]['text'],export['rejected'])
        with self.assertRaises(ValueError):pipeline.edit_session(self.session,[export,export])

    def test_empty_scenes_do_not_call_model(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(common.codex_roles,'invoke',side_effect=AssertionError('No calls')):
            self.assertEqual(pipeline.compare_candidates(Path(directory),[]),[])


if __name__=='__main__':unittest.main()
