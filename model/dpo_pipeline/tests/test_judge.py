"""원척도 보존·언어 원인 연결·모든 턴·미래 인용 차단 계약 검사."""
import copy
from pathlib import Path
import tempfile
import unittest

from cbt_dpo import judge as task


class OriginalRubricExtensionTests(unittest.TestCase):
    def setUp(self):
        self.session={'conversation_id':'test','provided_context':'사전 제공 사실',
            'turns':[{'role':'client','text':'부담스러워요.'},
                {'role':'therapist','text':'그 마음을 自我保护라고만 부르겠습니다.'},
                {'role':'client','text':'무슨 뜻인지 모르겠어요.'}]}
        self.payload=task.payload_for(self.session,'general_1_understanding')
        self.output={'request_id':self.payload['request_id'],'item':'general_1_understanding',
            'raw_response':'3, 공감은 있으나 설명 없는 중국어 혼입으로 이해를 전달하는 데 한계가 있다.',
            'language_findings':[{'turn_id':2,'quote':'自我保护','classification':'problematic',
                'reason':'설명 없는 중국어가 한국어 문장의 이해를 방해한다.',
                'affects_item':False,'criterion_quote':''}],
            'turn_reviews':[{'turn_id':2,'decision':'appropriate','reason':'감정을 다루려는 시도는 있다.',
                'evidence':[{'turn_id':2,'quote':self.session['turns'][1]['text']}],
                'criterion_quote':'','rewrite_hint':''}],
            'session_limits':[],'limitations':'모의 입력이다.'}

    def test_original_template_is_preserved_as_substring(self):
        prompt=task.render_prompt(self.session,self.payload)
        item=next(i for i in task.load_prompts(task.RUBRICS) if i.item=='general_1_understanding')
        original=item.render(task.parse_conversation(self.session).to_judge_text())
        self.assertIn(task.INSTRUCTIONS+'\n\n'+original,prompt)
        self.assertEqual(set(task.ITEMS),{i.item for i in task.load_prompts(task.RUBRICS)})

    def test_language_observation_is_not_automatic_penalty(self):
        self.assertEqual(task.validate(self.output,self.payload).score,3)

    def test_foreign_candidate_cannot_silently_disappear(self):
        self.output['language_findings']=[]
        with self.assertRaises(ValueError):task.validate(self.output,self.payload)

    def test_legitimate_foreign_term_may_be_permitted(self):
        self.output['language_findings'][0]['classification']='permitted'
        self.output['language_findings'][0]['reason']='검사 계약상 허용 분류도 가능하다.'
        task.validate(self.output,self.payload)

    def test_language_influence_requires_rubric_and_explanation(self):
        row=self.output['language_findings'][0];row['affects_item']=True
        with self.assertRaises(ValueError):task.validate(self.output,self.payload)
        row['criterion_quote']=task.definitions('general_1_understanding').splitlines()[-1]
        task.validate(self.output,self.payload)
        self.output['raw_response']='3, 공감과 이해의 일부 한계가 있다.'
        with self.assertRaises(ValueError):task.validate(self.output,self.payload)

    def test_language_influence_may_be_explicit_through_the_actual_foreign_quote(self):
        row=self.output['language_findings'][0]
        row['affects_item']=True
        row['criterion_quote']=task.definitions('general_1_understanding').splitlines()[-1]
        self.output['raw_response']='3, 설명 없는 自我保护 삽입이 명료한 이해 전달을 방해한다.'
        task.validate(self.output,self.payload)

    def test_every_therapist_turn_is_required(self):
        self.output['turn_reviews']=[]
        with self.assertRaises(ValueError):task.validate(self.output,self.payload)

    def test_prefix_evidence_cannot_include_future_reaction(self):
        self.output['turn_reviews'][0]['evidence'].append({'turn_id':3,'quote':'무슨 뜻인지 모르겠어요.'})
        with self.assertRaises(ValueError):task.validate(self.output,self.payload)

    def test_no_turn_score_and_no_seventh_item(self):
        self.assertNotIn('score',task.SCHEMA['properties']['turn_reviews']['items']['properties'])
        self.assertEqual(len(task.ITEMS),6)

    def test_structure_may_cross_reference_already_quoted_turn_reviews(self):
        self.session['turns'].append({'role':'therapist','text':'말씀을 듣겠습니다.'})
        self.payload=task.payload_for(self.session,'general_1_understanding')
        self.output['request_id']=self.payload['request_id']
        self.output['turn_reviews'].append({'turn_id':4,'decision':'appropriate','reason':'경청한다.',
            'evidence':[{'turn_id':4,'quote':'말씀을 듣겠습니다.'}],'criterion_quote':'','rewrite_hint':''})
        self.output['session_limits']=[{'scope':'session_structure','turn_ids':[2,4],
            'reason':'회기 전체의 이해 확인 기회가 제한됐다.',
            'criterion_quote':task.definitions('general_1_understanding').splitlines()[-1],
            'evidence':[{'turn_id':2,'quote':'自我保护'}]}]
        task.validate(self.output,self.payload)
        self.output['session_limits'][0]['turn_ids'].append(999)
        with self.assertRaises(ValueError):task.validate(self.output,self.payload)

    def test_client_feedback_can_anchor_structure_but_not_be_a_problem_turn(self):
        self.output['session_limits']=[{'scope':'session_structure','turn_ids':[1,2],
            'reason':'내담자의 피드백과 상담자 반응을 연결한 구조 근거다.',
            'criterion_quote':task.definitions('general_1_understanding').splitlines()[-1],
            'evidence':[{'turn_id':1,'quote':'부담스러워요.'}]}]
        task.validate(self.output,self.payload)
        self.output['session_limits'][0]['scope']='repeated_pattern'
        self.output['session_limits'][0]['turn_ids']=[1]
        with self.assertRaises(ValueError):task.validate(self.output,self.payload)

    def test_repeated_client_feedback_is_valid_session_evidence(self):
        self.output['session_limits']=[{'scope':'repeated_pattern','turn_ids':[1,3],
            'reason':'내담자가 반응의 어려움을 반복해서 전달한 맥락이다.',
            'criterion_quote':task.definitions('general_1_understanding').splitlines()[-1],
            'evidence':[{'turn_id':1,'quote':'부담스러워요.'},{'turn_id':3,'quote':'무슨 뜻인지 모르겠어요.'}]}]
        task.validate(self.output,self.payload)

    def test_session_evidence_may_be_feedback_for_already_quoted_therapist_turn(self):
        self.output['session_limits']=[{'scope':'session_structure','turn_ids':[2],
            'reason':'대상 상담자 응답 이후 내담자가 명료성 문제를 밝혔다.',
            'criterion_quote':task.definitions('general_1_understanding').splitlines()[-1],
            'evidence':[{'turn_id':3,'quote':'무슨 뜻인지 모르겠어요.'}]}]
        task.validate(self.output,self.payload)
        self.output['turn_reviews'][0]['evidence'].append({'turn_id':3,'quote':'무슨 뜻인지 모르겠어요.'})
        with self.assertRaises(ValueError):task.validate(self.output,self.payload)

    def test_detector_handles_multiple_scripts_without_classifying_errors(self):
        values=task.script_candidates('한국어 自我保护 CBT Привет')
        self.assertEqual([v['text'] for v in values],['自我保护','CBT','Привет'])

    def test_low_score_gate_waits_for_six_and_uses_unrounded_mean(self):
        for scores,enabled in [([4]*5,False),([4]*5+[3],False),([4]*4+[3,3],True)]:
            with self.subTest(scores=scores),tempfile.TemporaryDirectory() as directory:
                folder=Path(directory)
                for item,score in zip(task.ITEMS,scores):
                    result=copy.deepcopy(self.output);result['item']=item
                    task.shared.write_json(folder/'results'/(item+'.json'),{'item':item,'score':score,
                        'explanation':'모의 집계','result':result})
                summary=task.summarize(folder)
                self.assertEqual(summary['low_score_analysis_enabled'],enabled)
                if len(scores)<6:self.assertIsNone(summary['mean'])
                if enabled:
                    self.assertEqual(summary['low_score_turn_index'][0]['needs_improvement_items'],[])
                else:self.assertIsNone(summary['low_score_turn_index'])

    def test_quote_audit_cannot_modify_score_or_diagnosis(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            audit={'raw_output_sha256':task.shared.digest(self.output),
                'corrections':[{'path':['raw_response'],'old':self.output['raw_response'],'new':'6, 우수','reason':'차단 검사'}]}
            task.shared.write_json(folder/'quote_audits/general_1_understanding.json',audit)
            with self.assertRaises(ValueError):task.resolve_quote_audit(folder,'general_1_understanding',self.output,self.payload)

    def test_criterion_case_only_difference_is_allowed_but_wording_change_is_not(self):
        definition=task.definitions('CBT_2_focus')
        quote='Therapist could have focused on more central cognitions or behaviors that offered greater promise for progress.'
        task.check_criterion_quote(quote,definition)
        with self.assertRaises(ValueError):task.check_criterion_quote(quote.replace('more central','less central'),definition)

    def test_quote_audit_replays_only_an_exact_source_correction(self):
        raw=copy.deepcopy(self.output)
        raw['turn_reviews'][0]['evidence'][0]['quote']='원문에 없는 그 마음'
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            task.shared.write_json(folder/'quote_audits/general_1_understanding.json',{
                'raw_output_sha256':task.shared.digest(raw),'corrections':[{
                    'path':['turn_reviews',0,'evidence',0,'quote'],'old':'원문에 없는 그 마음',
                    'new':self.session['turns'][1]['text'],'reason':'실제 같은 번호 원문으로 인용만 정렬'}]})
            result=task.resolve_quote_audit(folder,'general_1_understanding',raw,self.payload)
            task.validate(result,self.payload)
            self.assertEqual(result['raw_response'],raw['raw_response'])
            self.assertEqual(raw['turn_reviews'][0]['evidence'][0]['quote'],'원문에 없는 그 마음')

    def test_session_source_audit_only_repairs_unique_session_evidence(self):
        raw=copy.deepcopy(self.output)
        raw['session_limits']=[{'evidence':[{'turn_id':1,'quote':'무슨 뜻인지 모르겠어요.'}]}]
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            task.shared.write_json(folder/'raw_outputs/general_1_understanding.json',raw)
            audit={'raw_output_sha256':task.shared.digest(raw),'corrections':[{
                'path':['session_limits',0,'evidence',0,'turn_id'],'old':1,'new':3,
                'reason':'정확한 인용은 대화3에만 있다.'}]}
            path=folder/'evidence_source_audits/general_1_understanding.json'
            task.shared.write_json(path,audit)
            result=task.resolve_quote_audit(folder,'general_1_understanding',raw,self.payload)
            self.assertEqual(result['session_limits'][0]['evidence'][0]['turn_id'],3)
            self.assertEqual(result['raw_response'],raw['raw_response'])
            self.assertEqual(result['turn_reviews'],raw['turn_reviews'])
            self.assertEqual(raw['session_limits'][0]['evidence'][0]['turn_id'],1)
            # 개별 턴의 번호·미래 근거·점수 교정으로 이 경로를 사용할 수 없다.
            for invalid in [['turn_reviews',0,'evidence',0,'turn_id'],['raw_response']]:
                audit['corrections'][0]['path']=invalid
                task.shared.write_json(path,audit)
                with self.assertRaises(ValueError):
                    task.resolve_quote_audit(folder,'general_1_understanding',raw,self.payload)
            audit['corrections'][0]['path']=['session_limits',0,'evidence',0,'turn_id']
            audit['corrections'][0]['new']=2
            task.shared.write_json(path,audit)
            with self.assertRaises(ValueError):
                task.resolve_quote_audit(folder,'general_1_understanding',raw,self.payload)


if __name__=='__main__':unittest.main()
