import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ctrs_judge.client import Completion
from ctrs_judge.conversation import load_conversations, parse_conversation
from ctrs_judge.parse import parse_response
from ctrs_judge.prompts import load_prompts
from ctrs_judge.runner import run

CONV = {"conversation_id": "c1", "turns": [
    {"role": "client", "text": "요즘 잠이 안 와요."}, {"role": "therapist", "text": "많이 힘드시겠어요."}]}


class ParseTest(unittest.TestCase):
    def test_first_comma_only(self):
        p = parse_response("4, Good reflection, but missed subtle cues, overall fine.")
        self.assertTrue(p.ok)
        self.assertEqual(p.score, 4)
        self.assertEqual(p.explanation, "Good reflection, but missed subtle cues, overall fine.")

    def test_rejects_bad(self):
        for raw in ["", None, "no comma here", "7, too high", "4.5, float", "Score: 4, prefix", "-1, neg", "four, word"]:
            self.assertFalse(parse_response(raw).ok, raw)

    def test_zero_ok(self):
        self.assertEqual(parse_response("0, none").score, 0)


class PromptTest(unittest.TestCase):
    def test_real_prompts_load_and_render(self):
        items = load_prompts()
        self.assertGreaterEqual(len(items), 4)
        for it in items:
            out = it.render("Client: hi")
            self.assertIn("Client: hi", out)
            self.assertNotIn("{conversation}", out)

    def test_new_file_adds_item(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.txt").write_text("x {conversation}")
            self.assertEqual([i.item for i in load_prompts(d)], ["a"])
            (Path(d) / "b.txt").write_text("y {conversation} {other}")
            items = load_prompts(d)
            self.assertEqual([i.item for i in items], ["a", "b"])
            self.assertIn("{other}", items[1].render("T"))  # 다른 중괄호 보존

    def test_missing_placeholder(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.txt").write_text("no placeholder")
            with self.assertRaises(ValueError):
                load_prompts(d)


class ConversationTest(unittest.TestCase):
    def test_to_text(self):
        self.assertEqual(parse_conversation(CONV).to_text(), "Client: 요즘 잠이 안 와요.\nTherapist: 많이 힘드시겠어요.")

    def test_invalid(self):
        with self.assertRaises(ValueError):
            parse_conversation({"conversation_id": "x", "turns": [{"role": "bot", "text": "a"}]})


class RunnerTest(unittest.TestCase):
    def test_run_resume_and_failures(self):
        calls = []
        responses = iter(["4, ok, fine", "garbage"])

        def fake(prompt):
            calls.append(prompt)
            return Completion(next(responses), "m-snap", 100, 0, 10, 0.1, 0)

        with tempfile.TemporaryDirectory() as d:
            inp = Path(d) / "in.jsonl"
            inp.write_text(json.dumps(CONV, ensure_ascii=False) + "\n")
            convs = load_conversations(inp)
            items = load_prompts()[:2]
            cfg = {"temperature": 0, "input_usd_per_million": 1, "output_usd_per_million": 1}
            out = Path(d) / "out.jsonl"
            stats = run(convs, items, {"m": (cfg, fake)}, out, workers=1)
            self.assertEqual((stats["parsed"], stats["parse_failed"]), (1, 1))
            rows = [json.loads(l) for l in out.read_text().splitlines()]
            self.assertEqual(rows[0]["score"], 4)
            self.assertEqual(rows[0]["explanation"], "ok, fine")
            self.assertIn("많이 힘드시겠어요", rows[0]["conversation"])
            self.assertEqual(rows[1]["raw_response"], "garbage")  # 실패 원문 보존
            # 재실행하면 완료분 건너뜀
            self.assertEqual(run(convs, items, {"m": (cfg, fake)}, out, workers=1)["total"], 0)


class CactusKoTest(unittest.TestCase):
    def test_convert(self):
        from ctrs_judge.cactus_ko import convert, parse_dialogue
        t = parse_dialogue("상담사: 안녕하세요: 반가워요\n내담자: 네")
        self.assertEqual(t, [{"role": "therapist", "text": "안녕하세요: 반가워요"}, {"role": "client", "text": "네"}])
        rows = convert([{"dialogue": "상담사: a\n내담자: b", "attitude": "중립적", "intake_form": "x"}])
        self.assertEqual(rows[0]["conversation_id"], "cactus_ko_0000")
        self.assertNotIn("intake_form", rows[0]["meta"])
        parse_conversation(rows[0])

    def test_unknown_speaker(self):
        from ctrs_judge.cactus_ko import parse_dialogue
        with self.assertRaises(ValueError):
            parse_dialogue("의사: 안녕")


class PerturbTest(unittest.TestCase):
    BASE = {"conversation_id": "b1", "meta": {}, "turns": [
        {"role": "therapist", "text": "안녕하세요. 반가워요."}, {"role": "client", "text": "네."},
        {"role": "therapist", "text": "힘드셨겠어요. 언제부터였나요?"}, {"role": "client", "text": "작년요."},
        {"role": "therapist", "text": "그렇군요. 그때 무슨 생각이 들었나요?"}, {"role": "client", "text": "몰라요."}]}

    def test_repeat_and_no_empathy(self):
        from ctrs_judge.perturb import make_variant
        r = make_variant(self.BASE, "repeat")
        self.assertEqual(r["turns"][4]["text"], "힘드셨겠어요. 언제부터였나요?")
        self.assertEqual(r["meta"]["expected_drop"], "general_1_understanding")
        e = make_variant(self.BASE, "no_empathy")
        self.assertEqual(e["turns"][2]["text"], "언제부터였나요?")
        self.assertEqual(e["turns"][0]["text"], "안녕하세요. 반가워요.")  # 인사 유지
        self.assertEqual(self.BASE["turns"][2]["text"], "힘드셨겠어요. 언제부터였나요?")  # 원본 불변

    def test_cold(self):
        from ctrs_judge.perturb import make_variant
        c = make_variant(self.BASE, "cold")
        t = [x["text"] for x in c["turns"] if x["role"] == "therapist"]
        self.assertEqual(t[0], "안녕하세요. 반가워요.")           # 인사 유지
        self.assertTrue(t[1].endswith("언제부터였나요?"))         # 질문(마지막 문장)은 유지
        self.assertNotIn("힘드셨겠어요", t[1])                    # 공감 문장은 제거
        self.assertNotEqual(t[1], "언제부터였나요?")               # no_empathy와 달리 차가운 말투가 붙음
        self.assertEqual(c["meta"]["expected_drop"], "general_2_interpersonal_effectiveness")

    def test_severity(self):
        from ctrs_judge.perturb import make_variant
        turns = []
        for k in range(10):
            turns += [{"role": "therapist", "text": f"공감 {k}. 질문 {k}?"}, {"role": "client", "text": f"답 {k}"}]
        base = {"conversation_id": "s1", "meta": {}, "turns": turns}
        changed = lambda v: sum(1 for x, y in zip(turns, v["turns"]) if x["text"] != y["text"])  # noqa: E731
        full, p60, p30 = (make_variant(base, "no_empathy", severity=s) for s in (100, 60, 30))
        self.assertEqual((changed(full), changed(p60), changed(p30)), (9, 5, 3))  # 첫 인사 제외 9개 중
        self.assertTrue(full["conversation_id"].endswith("__no_empathy"))   # 100%는 기존 id 유지
        self.assertTrue(p60["conversation_id"].endswith("__no_empathy_p60"))
        self.assertEqual(p30["meta"]["severity"], 30)
        # 30%가 바꾼 발화는 모두 100%에서도 바뀐 발화(부분집합)이고 결정적
        again = make_variant(base, "no_empathy", severity=30)
        self.assertEqual(p30["turns"], again["turns"])
        # 정도와 무관하게 내담자 발화와 원본 불변
        self.assertEqual([t["text"] for t in p30["turns"] if t["role"] == "client"],
                         [t["text"] for t in turns if t["role"] == "client"])

    def test_template_variants(self):
        from ctrs_judge.perturb import make_variant
        for kind in ("lecture", "directive", "offtopic"):
            v = make_variant(self.BASE, kind)  # API 없이 생성
            t = [x["text"] for x in v["turns"] if x["role"] == "therapist"]
            self.assertEqual(t[0], "안녕하세요. 반가워요.")
            self.assertNotEqual(t[1], self.BASE["turns"][2]["text"])
            self.assertEqual(v["turns"][1]["text"], "네.")

    def test_llm_rewrite_validates_count(self):
        from ctrs_judge.perturb import make_variant
        outs = iter(['["a", "b"]', '```json\n["x", "y", "z"]\n```'])  # 개수 불일치 후 재시도 성공
        v = make_variant(self.BASE, "lecture", lambda p: next(outs))
        self.assertEqual([t["text"] for t in v["turns"] if t["role"] == "therapist"],
                         ["안녕하세요. 반가워요.", "y", "z"])
        self.assertEqual(v["turns"][1]["text"], "네.")  # 내담자 발화 불변


class AnalyzeTest(unittest.TestCase):
    def _run(self, d):
        from ctrs_judge.conversation import parse_conversation as pc
        base = {"conversation_id": "b1", "meta": {"perturbation": "original", "base_id": "b1"},
                "turns": [{"role": "therapist", "text": "a"}, {"role": "client", "text": "b"}]}
        bad = {"conversation_id": "b1__repeat", "turns": base["turns"],
               "meta": {"perturbation": "repeat", "base_id": "b1", "expected_drop": "general_1_understanding"}}
        convs = [pc(base), pc(bad)]
        items = load_prompts()
        n = {"i": 0}

        def fake(prompt):
            n["i"] += 1
            # 망가진 대화(문장 "a"/"b"는 동일하므로 호출 순서가 아니라 모델별 고정값 사용)
            return Completion("4, 설명, 쉼표 포함", "m", 10, 0, 5, 0.1, 0)

        out = Path(d) / "r.jsonl"
        run(convs, items, {"m1": ({"temperature": 0}, fake), "m2": ({}, fake)}, out, runs=2, workers=1)
        return out

    def test_summarize_runs(self):
        from ctrs_judge.analyze import explanations, load_rows, summarize, to_csv
        with tempfile.TemporaryDirectory() as d:
            rows = load_rows(self._run(d))
            self.assertEqual(len(rows), 2 * 2 * 6 * 2)
            text = summarize(rows)
            for s in ("실행 요약", "점수 분포", "항목별 평균", "모델 간 일치도", "변별력", "일관성", "이해"):
                self.assertIn(s, text)
            self.assertIn("설명, 쉼표 포함", explanations(rows, "b1", "general_1_understanding"))
            to_csv(rows, Path(d) / "o.csv")
            self.assertIn("conversation_id", (Path(d) / "o.csv").read_text(encoding="utf-8-sig"))

    def test_success_not_overwritten_by_failure(self):
        from ctrs_judge.analyze import load_rows
        ok = {"conversation_id": "c", "judge": "j", "item": "i", "run_index": 1, "api_error": None, "score": 4, "parse_ok": True}
        bad = {**ok, "api_error": "x", "score": None, "parse_ok": False}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.jsonl"
            p.write_text(json.dumps(ok) + "\n" + json.dumps(bad) + "\n")
            self.assertEqual(load_rows(p)[0]["score"], 4)


class RelaxedTest(unittest.TestCase):
    def test_relaxed_prompts(self):
        import subprocess
        root = Path(__file__).resolve().parent.parent
        subprocess.run([sys.executable, str(root / "make_relaxed_prompts.py")], check=True, capture_output=True)
        orig, relaxed = load_prompts(root / "prompts"), load_prompts(root / "prompts_relaxed")
        self.assertEqual([i.item for i in orig], [i.item for i in relaxed])
        for o, r in zip(orig, relaxed):
            low = r.template.lower()
            self.assertNotIn("strict", low)
            self.assertNotIn("deficiency", low)
            self.assertIn("Assign a score based on the criteria.", r.template)
            self.assertIn("[Evaluation Question]", r.template)  # 나머지 구조는 유지
            self.assertNotEqual(o.sha256, r.sha256)

    def test_compare_runs(self):
        from ctrs_judge.analyze import compare, load_rows
        with tempfile.TemporaryDirectory() as d:
            ra = AnalyzeTest()._run(d)
            text = compare(load_rows(ra), load_rows(ra), "m1", "엄격", "완화")
            for s in ("정상 대화의 점수 분포", "항목별 평균", "망가진 대화", "일치"):
                self.assertIn(s, text)


class RankTest(unittest.TestCase):
    def test_spearman(self):
        from ctrs_judge.analyze import spearman
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertIsNone(spearman([4, 4, 4, 4], [1, 2, 3, 4]))   # 한쪽이 상수면 계산 불가
        self.assertAlmostEqual(spearman([1, 2, 2, 3], [1, 2, 2, 3]), 1.0)  # 동점 처리

    def test_rank_agreement_runs(self):
        from ctrs_judge.analyze import load_rows, rank_agreement
        with tempfile.TemporaryDirectory() as d:
            rows = load_rows(AnalyzeTest()._run(d))
            text = rank_agreement(rows, "m1", rows, "m2")
            self.assertIn("순위 상관", text)
            self.assertIn("계산 불가", text)  # 가짜 judge는 점수가 모두 같음


if __name__ == "__main__":
    unittest.main()
