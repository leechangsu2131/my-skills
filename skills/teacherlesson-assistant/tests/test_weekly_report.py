"""weekly_report.py 시험. 임시 폴더의 가짜 sessions 만 쓴다(학생 이름은 '학생A')."""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from datetime import date
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import weekly_report as wr  # noqa: E402


class WeeklyReportTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data = pathlib.Path(tmp.name)

    def session(self, day, period, subject, memos, publisher="가출판"):
        folder = self.data / "sessions" / day
        folder.mkdir(parents=True, exist_ok=True)
        rec = {"date": day, "subject": subject, "publisher": publisher, "title": "분수",
               "memos": [{"kind": k, "text": t} for k, t in memos]}
        (folder / f"{period}교시_{subject}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")

    def report(self, day=date(2026, 11, 26)):
        path, count, broken = wr.make_report(self.data, day)
        return path, path.read_text(encoding="utf-8"), count, broken

    def parts(self, text):
        body, rest = text.split("## 출판사 주의점 후보")
        candidates, students = rest.split("## 🙋 학생별 발표 메모")
        return body, candidates, students

    def test_week_range_file_name_and_grouping(self):
        self.session("2026-11-23", 1, "수학", [("fix", "분수 막대 부족"), ("good", "놀이 좋았음")])
        self.session("2026-11-29", 2, "사회", [("note", "일요일 메모")], publisher="")
        self.session("2026-11-22", 1, "수학", [("fix", "지난주 것")])
        self.session("2026-11-30", 1, "수학", [("fix", "다음주 것")])
        path, text, count, _ = self.report()
        self.assertEqual(path, self.data / "reports" / "week-2026-11-23.md")
        self.assertEqual(count, 2)
        self.assertIn("### 수학 (가출판)", text)
        self.assertIn("### 사회 (출판사 확인 필요)", text)
        self.assertIn("분수 막대 부족", text)
        self.assertNotIn("지난주 것", text)
        self.assertNotIn("다음주 것", text)

    def test_student_names_stay_in_student_section(self):
        self.session("2026-11-16", 1, "국어", [("student", "학생B 지난주 발표")])
        self.session("2026-11-23", 1, "수학", [
            ("student", "학생A가 풀이를 설명함"), ("fix", "학생A 질문에 시간 씀"), ("note", "학생B 자리 바꾸기")])
        _, text, _, _ = self.report()
        body, candidates, students = self.parts(text)
        for name in ("학생A", "학생B"):
            self.assertNotIn(name, body)
            self.assertNotIn(name, candidates)
        self.assertIn("(학생) 질문에 시간 씀", body)
        self.assertNotIn("질문에 시간 씀", candidates)
        self.assertIn("### 학생A가", students)
        self.assertNotIn("지난주 발표", students)

    def test_candidates_skip_known_and_mark_repeats_without_writing_notes(self):
        notes = {"가출판|수학": [{"text": "이미 적은 것", "date": "2026-11-01"}]}
        notes_path = self.data / "publisher_notes.json"
        notes_path.write_text(json.dumps(notes, ensure_ascii=False), encoding="utf-8")
        before = notes_path.read_bytes()
        self.session("2026-11-23", 1, "수학", [("fix", "이미 적은 것"), ("fix", "개념 설명이 단순")])
        self.session("2026-11-24", 1, "수학", [("fix", "개념 설명이 단순"), ("good", "활동 좋음")])
        _, candidates, _ = self.parts(self.report()[1])
        self.assertEqual(candidates.count("- [ ] 개념 설명이 단순"), 1)
        self.assertIn("2개 수업", candidates)
        self.assertNotIn("이미 적은 것", candidates)
        self.assertNotIn("활동 좋음", candidates)
        self.assertEqual(notes_path.read_bytes(), before)

    def test_system_records_are_left_out_and_broken_file_is_counted(self):
        self.session("2026-11-23", 1, "수학", [("sys", "수업 시작"), ("step", "단계: 도입"), ("adj", "시간 조정"), ("star", "(표시)")])
        (self.data / "sessions" / "2026-11-23" / "2교시_국어.json").write_text("{", encoding="utf-8")
        _, text, count, broken = self.report()
        self.assertEqual((count, broken), (1, 1))
        for word in ("수업 시작", "단계: 도입", "시간 조정", "(표시)"):
            self.assertNotIn(word, text)

    def test_empty_week_and_console_output_has_no_memo_text(self):
        self.assertIn("메모가 없습니다", self.report()[1])
        self.session("2026-11-23", 1, "수학", [("student", "학생A 발표함"), ("fix", "비밀 메모")])
        out = io.StringIO()
        with mock.patch.object(wr, "data_dir", lambda *a: self.data), contextlib.redirect_stdout(out):
            wr.main(["--date", "2026-11-26"])
        self.assertIn("1개", out.getvalue())
        self.assertNotIn("학생A", out.getvalue())
        self.assertNotIn("비밀 메모", out.getvalue())


if __name__ == "__main__":
    unittest.main()
