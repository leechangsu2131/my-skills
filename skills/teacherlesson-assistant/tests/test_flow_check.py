import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import flow_check as fc  # noqa: E402


def flow(**changes):
    value = {
        "goal": "분수의 덧셈 원리를 설명한다",
        "steps": [
            {"name": "도입", "minutes": 10, "teacher_actions": ["문제를 보여 준다"]},
            {"name": "탐구", "minutes": 20, "student_actions": ["분수 막대로 알아본다"]},
            {"name": "정리", "minutes": 10, "check": "원리를 말하는지 확인"},
        ],
    }
    value.update(changes)
    return value


class CheckFlowTests(unittest.TestCase):
    def assertIssue(self, value, text):
        self.assertTrue(any(text in issue for issue in fc.check_flow(value)), fc.check_flow(value))

    def test_good_new_flow(self):
        self.assertEqual(fc.check_flow(flow()), [])

    def test_35_and_45_minutes_are_allowed(self):
        for minutes in (5, 15):
            value = flow()
            value["steps"][0]["minutes"] = minutes
            self.assertFalse(any("시간 합계" in issue for issue in fc.check_flow(value)))

    def test_too_short(self):
        self.assertIssue(flow(steps=[{"name": "도입", "minutes": 34}]), "시간 합계")

    def test_too_long(self):
        self.assertIssue(flow(steps=[{"name": "활동", "minutes": 46}]), "시간 합계")

    def test_no_steps(self):
        self.assertIssue(flow(steps=[]), "단계 없음")

    def test_blank_step_name(self):
        self.assertIssue(flow(steps=[{"name": " ", "minutes": 40}]), "이름 없음")

    def test_zero_minutes(self):
        self.assertIssue(flow(steps=[{"name": "도입", "minutes": 0}]), "0 이하")

    def test_negative_minutes(self):
        self.assertIssue(flow(steps=[{"name": "도입", "minutes": -5}]), "0 이하")

    def test_non_number_minutes(self):
        self.assertIssue(flow(steps=[{"name": "도입", "minutes": "40"}]), "숫자가 아님")

    def test_duplicate_names_ignore_spacing_and_case(self):
        self.assertIssue(flow(steps=[{"name": "Talk", "minutes": 20}, {"name": " talk ", "minutes": 20}]), "같은 단계명 반복")

    def test_missing_goal(self):
        self.assertIssue(flow(goal=""), "차시 목표 없음")

    def test_old_flow_is_allowed(self):
        old = flow(steps=[{"name": "도입", "minutes": 40, "do": "그림 보기", "say": "무엇일까요?"}])
        self.assertFalse(any("섞임" in issue for issue in fc.check_flow(old)))

    def test_mixed_old_and_new_fields(self):
        mixed = flow(steps=[{"name": "도입", "minutes": 40, "do": "그림 보기", "teacher_actions": ["그림을 보여 준다"]}])
        self.assertIssue(mixed, "섞임")

    def test_non_object_step_and_root(self):
        self.assertIssue(flow(steps=["깨짐"]), "객체가 아님")
        self.assertIssue([], "맨 위가 객체가 아님")


class GuideTests(unittest.TestCase):
    def test_ratio_counts_unique_words(self):
        value = flow(goal="분수 덧셈", steps=[{"name": "탐구", "minutes": 40, "do": "분수 막대 탐구"}])
        missing, total, ratio = fc.guide_word_ratio(value, "분수 덧셈 원리 막대")
        self.assertEqual((missing, total), (1, 4))
        self.assertEqual(ratio, 0.25)

    def test_empty_flow_words_has_no_ratio(self):
        self.assertEqual(fc.guide_word_ratio({"steps": []}, "지도서"), (0, 0, None))


class FileAndCliTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name)

    def test_broken_json_is_reported(self):
        path = self.root / "broken.json"
        path.write_text("{", encoding="utf-8")
        self.assertIn("JSON 읽기 실패", fc.check_file(path)["issues"][0])

    def test_cli_prints_table_and_does_not_change_files(self):
        path = self.root / "lesson.json"
        original = json.dumps(flow(), ensure_ascii=False)
        path.write_text(original, encoding="utf-8")
        guide = self.root / "guide.md"
        guide.write_text("분수 덧셈 원리 문제 탐구 정리", encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(fc.main([str(self.root), "--guide", str(guide)]), 0)
        self.assertIn("| lesson.json |", output.getvalue())
        self.assertIn("지도서에 없는 낱말", output.getvalue())
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_table_without_guide_uses_dash(self):
        result = {"path": pathlib.Path("a.json"), "issues": [], "guide": None}
        self.assertIn("| a.json | 정상 | - |", fc.render_table([result]))


if __name__ == "__main__":
    unittest.main()
