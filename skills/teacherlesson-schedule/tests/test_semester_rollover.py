"""semester_rollover.py 의 순수 함수 시험 (S1) — 진도표(구글 시트)에 연결하지 않고 JSON 파일·딕셔너리만 쓴다.

`main()` 은 시트에 읽고 쓰는 일이라 여기서 다루지 않는다. 학기 넘김에서 '어디까지 완료로 칠지'(mark_until·matches)와
'새 학기 행을 어떻게 읽어 붙일지'(load_new_rows)는 틀리면 수업이 통째로 어긋나서 따로 시험한다.
"""
import json
import tempfile
import unittest
from pathlib import Path

import semester_rollover as sr

DONE = sr.DONE


def row(unit, title, done=False, **extra):
    return {"대단원": unit, "수업내용": title, DONE: done, **extra}


class NormTests(unittest.TestCase):
    def test_removes_all_whitespace(self):
        self.assertEqual(sr.norm(" 1.  만나요,\t음악 \n시간 "), "1.만나요,음악시간")

    def test_none_and_numbers(self):
        self.assertEqual(sr.norm(None), "")
        self.assertEqual(sr.norm(12), "12")
        self.assertEqual(sr.norm(""), "")


class MatchesTests(unittest.TestCase):
    def test_unit_and_title_are_substring_ignoring_spaces(self):
        r = row("1. 만나요, 음악 시간", "구슬비 노래 부르기")
        self.assertTrue(sr.matches(r, {"unit": "만나요,음악시간", "title": "구슬비노래"}))

    def test_both_must_match(self):
        r = row("1. 만나요, 음악 시간", "구슬비 노래 부르기")
        self.assertFalse(sr.matches(r, {"unit": "2. 함께해요", "title": "구슬비"}))
        self.assertFalse(sr.matches(r, {"unit": "만나요", "title": "리듬 치기"}))

    def test_missing_keys_in_rule_match_everything(self):
        r = row("1. 만나요", "구슬비")
        self.assertTrue(sr.matches(r, {}))
        self.assertTrue(sr.matches(r, {"title": "구슬비"}))
        self.assertTrue(sr.matches(r, {"unit": "만나요"}))

    def test_row_missing_fields_does_not_match_a_real_rule(self):
        self.assertFalse(sr.matches({}, {"unit": "만나요"}))
        self.assertFalse(sr.matches({"대단원": None, "수업내용": None}, {"title": "구슬비"}))
        self.assertTrue(sr.matches({}, {}))  # 빈 규칙은 빈 행에도 맞는다(의도된 동작은 아니지만 지금 동작)


class MarkUntilTests(unittest.TestCase):
    def rows(self):
        return [
            row("1. 만나요", "노래 부르기"),
            row("1. 만나요", "리듬 치기"),
            row("2. 함께해요", "합주하기"),
            row("2. 함께해요", "감상하기"),
        ]

    def test_marks_through_the_matching_row(self):
        rows = self.rows()
        changed = sr.mark_until(rows, {"unit": "만나요", "title": "리듬"})
        self.assertEqual(changed, 2)
        self.assertEqual([r[DONE] for r in rows], [True, True, False, False])

    def test_uses_the_last_matching_row(self):
        rows = self.rows()
        changed = sr.mark_until(rows, {"unit": "함께해요"})  # 2단원 두 행이 다 맞음 → 마지막 행까지
        self.assertEqual(changed, 4)
        self.assertTrue(all(r[DONE] for r in rows))

    def test_exclusive_stops_before_the_matching_row(self):
        rows = self.rows()
        changed = sr.mark_until(rows, {"unit": "함께해요", "title": "합주", "exclusive": True})
        self.assertEqual(changed, 2)
        self.assertEqual([r[DONE] for r in rows], [True, True, False, False])

    def test_exclusive_on_the_first_row_changes_nothing(self):
        rows = self.rows()
        self.assertEqual(sr.mark_until(rows, {"title": "노래", "exclusive": True}), 0)
        self.assertFalse(any(r[DONE] for r in rows))

    def test_already_done_rows_are_not_counted_or_changed(self):
        rows = self.rows()
        rows[0][DONE] = True
        rows[1][DONE] = "TRUE"  # 시트에서 읽은 글자 값
        changed = sr.mark_until(rows, {"title": "합주"})
        self.assertEqual(changed, 1)
        self.assertEqual(rows[1][DONE], "TRUE")  # 건드리지 않음
        self.assertIs(rows[2][DONE], True)
        self.assertIs(rows[3][DONE], False)

    def test_row_without_done_key_is_treated_as_not_done(self):
        rows = [{"대단원": "1. 만나요", "수업내용": "노래"}]
        self.assertEqual(sr.mark_until(rows, {"title": "노래"}), 1)
        self.assertIs(rows[0][DONE], True)

    def test_raises_when_nothing_matches(self):
        rows = self.rows()
        with self.assertRaises(ValueError):
            sr.mark_until(rows, {"title": "없는 차시"})
        self.assertFalse(any(r[DONE] for r in rows))  # 못 찾으면 아무것도 바꾸지 않는다

    def test_empty_rows_raise(self):
        with self.assertRaises(ValueError):
            sr.mark_until([], {"title": "노래"})


class LoadNewRowsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def write(self, name, data):
        path = self.dir / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def sample_rows(self):
        return [
            {"과목": "음악", "대단원": "2. 함께해요", "차시": 1, "수업내용": "합주", "비고": "원본"},
            {"과목": "음악", "대단원": "1. 만나요", "차시": 1, "수업내용": "노래", "비고": "원본"},
            {"과목": "음악", "대단원": "1. 만나요", "차시": 2, "수업내용": "리듬", "비고": "원본"},
            {"과목": "미술", "대단원": "1. 그리기", "차시": 1, "수업내용": "스케치", "비고": "원본"},
        ]

    def test_list_form_filters_subject_and_marks_not_done(self):
        path = self.write("a.json", self.sample_rows())
        rows = sr.load_new_rows({"append": [{"subject": "음악", "rows_file": path}]})
        self.assertEqual([r["수업내용"] for r in rows], ["합주", "노래", "리듬"])
        self.assertTrue(all(r[DONE] is False for r in rows))

    def test_dict_with_rows_key_and_dict_of_subjects(self):
        flat = self.write("b.json", {"rows": self.sample_rows()})
        by_subject = self.write("c.json", {"rows": {"음악": self.sample_rows()[:3], "미술": self.sample_rows()[3:]}})
        for path in (flat, by_subject):
            rows = sr.load_new_rows({"append": [{"subject": "미술", "rows_file": path}]})
            self.assertEqual([r["수업내용"] for r in rows], ["스케치"])

    def test_plain_dict_of_subjects_without_rows_key(self):
        path = self.write("d.json", {"음악": self.sample_rows()[:3], "미술": self.sample_rows()[3:]})
        rows = sr.load_new_rows({"append": [{"subject": "음악", "rows_file": path}]})
        self.assertEqual(len(rows), 3)

    def test_rename_units_and_note(self):
        path = self.write("e.json", self.sample_rows())
        spec = {"subject": "음악", "rows_file": path, "rename_units": {"1. 만나요": "1. 새 이름"}, "note": "3-2"}
        rows = sr.load_new_rows({"append": [spec]})
        self.assertEqual([r["대단원"] for r in rows], ["2. 함께해요", "1. 새 이름", "1. 새 이름"])
        self.assertTrue(all(r["비고"] == "3-2" for r in rows))

    def test_without_note_keeps_existing_note(self):
        path = self.write("f.json", self.sample_rows())
        rows = sr.load_new_rows({"append": [{"subject": "음악", "rows_file": path}]})
        self.assertTrue(all(r["비고"] == "원본" for r in rows))

    def test_unit_order_is_stable_and_unknown_units_go_last(self):
        path = self.write("g.json", self.sample_rows())
        spec = {"subject": "음악", "rows_file": path, "unit_order": ["1. 만나요"]}
        rows = sr.load_new_rows({"append": [spec]})
        # 정한 단원이 앞으로, 단원 안의 차시 순서는 그대로, 순서에 없는 단원은 뒤로
        self.assertEqual([r["수업내용"] for r in rows], ["노래", "리듬", "합주"])

    def test_several_specs_are_concatenated_in_order(self):
        path = self.write("h.json", self.sample_rows())
        cfg = {"append": [{"subject": "미술", "rows_file": path}, {"subject": "음악", "rows_file": path}]}
        rows = sr.load_new_rows(cfg)
        self.assertEqual([r["과목"] for r in rows], ["미술", "음악", "음악", "음악"])

    def test_no_append_gives_empty(self):
        self.assertEqual(sr.load_new_rows({}), [])
        self.assertEqual(sr.load_new_rows({"append": []}), [])

    def test_does_not_change_the_source_file(self):
        path = self.write("i.json", self.sample_rows())
        before = Path(path).read_text(encoding="utf-8")
        sr.load_new_rows({"append": [{"subject": "음악", "rows_file": path, "note": "x", "rename_units": {"1. 만나요": "y"}}]})
        self.assertEqual(Path(path).read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
