"""transcribe.py 시험. 임시 폴더의 가짜 녹음·가짜 받아쓰기 결과만 쓴다(학생 이름은 '학생A', faster-whisper 는 안 부름)."""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import transcribe as tr  # noqa: E402

DAY = "2026-11-26"
REC = "3교시_국어_101500.webm"


def at(sec):
    """수업 시작(10:15:00Z)에서 sec 초 뒤의 ISO 시각."""
    total = 10 * 3600 + 15 * 60 + sec
    return f"2026-11-26T{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}.000Z"


def memo(sec, kind, text, **extra):
    return {"t": "13:45", "at": at(sec), "kind": kind, "text": text, **extra}


SEGMENTS = [
    {"start": 5.0, "end": 12.0, "text": "오늘은 이야기를 읽어 볼 거예요."},
    {"start": 70.0, "end": 80.0, "text": "주인공은 왜 그랬을까요? 학생A가 말해 볼까요?"},
    {"start": 130.0, "end": 140.0, "text": "잘했어요."},
]
MEMOS = [
    memo(0, "sys", "수업 시작"),
    memo(1, "step", "단계: 도입", idx=0),
    memo(60, "step", "단계: 활동", idx=1),
    memo(75, "fix", "질문이 어려웠음"),
    memo(150, "sys", "수업 마침"),
]


class BasicsTests(unittest.TestCase):
    def test_fmt_time(self):
        self.assertEqual(tr.fmt_time(0), "00:00")
        self.assertEqual(tr.fmt_time(65.9), "01:05")
        self.assertEqual(tr.fmt_time(75 * 60 + 3), "75:03")
        self.assertEqual(tr.fmt_time(-5), "00:00")
        self.assertEqual(tr.fmt_time(None), "00:00")

    def test_count_questions(self):
        self.assertEqual(tr.count_questions("이게 뭘까요? 왜 그럴까요?"), 2)
        self.assertEqual(tr.count_questions("뭘까요??"), 1)
        self.assertEqual(tr.count_questions("그렇죠？ 네."), 1)
        self.assertEqual(tr.count_questions("물음표가 없어요."), 0)
        self.assertEqual(tr.count_questions("?"), 0)
        self.assertEqual(tr.count_questions(None), 0)

    def test_seconds_between_handles_missing_and_mixed_timezones(self):
        a, b = tr.parse_iso(at(0)), tr.parse_iso(at(30))
        self.assertEqual(tr.seconds_between(a, b), 30)
        self.assertIsNone(tr.seconds_between(None, b))
        self.assertIsNone(tr.seconds_between(a, tr.parse_iso("2026-11-26T10:15:30")))
        self.assertIsNone(tr.parse_iso("엉뚱한 글"))


class WindowTests(unittest.TestCase):
    def test_windows_pair_start_and_end(self):
        s = {"memos": [memo(0, "sys", "수업 시작"), memo(100, "sys", "수업 마침"),
                       memo(200, "sys", "수업 시작"), memo(300, "sys", "수업 마침")]}
        w = tr.recording_windows(s)
        self.assertEqual(len(w), 2)
        self.assertEqual(tr.seconds_between(w[0]["start"], w[0]["end"]), 100)

    def test_open_window_has_no_end(self):
        w = tr.recording_windows({"memos": [memo(0, "sys", "수업 시작")]})
        self.assertIsNone(w[0]["end"])

    def test_pick_window_exact_and_estimated(self):
        two = {"rec_files": ["a.webm", "b.webm"], "memos": [memo(0, "sys", "수업 시작"), memo(100, "sys", "수업 시작")]}
        w, exact = tr.pick_window(two, "b.webm")
        self.assertTrue(exact)
        self.assertEqual(tr.seconds_between(tr.parse_iso(at(0)), w["start"]), 100)
        # 마이크 없이 시작한 수업이 앞에 하나 더 있음 → 뒤에서부터 맞추고 추정
        extra = {"rec_files": ["a.webm"], "memos": [memo(0, "sys", "수업 시작"), memo(100, "sys", "수업 시작")]}
        w, exact = tr.pick_window(extra, "a.webm")
        self.assertFalse(exact)
        self.assertEqual(tr.seconds_between(tr.parse_iso(at(0)), w["start"]), 100)

    def test_pick_window_none_cases(self):
        self.assertEqual(tr.pick_window({"rec_files": ["a.webm"], "memos": []}, "a.webm"), (None, False))
        self.assertEqual(tr.pick_window({"rec_files": ["a.webm"], "memos": [memo(0, "sys", "수업 시작")]}, "z.webm"), (None, False))
        # 녹음이 '수업 시작' 보다 많으면 맞출 수 없음
        two = {"rec_files": ["a.webm", "b.webm"], "memos": [memo(0, "sys", "수업 시작")]}
        self.assertEqual(tr.pick_window(two, "a.webm"), (None, False))

    def test_window_entries_offsets_and_range(self):
        s = {"memos": MEMOS + [memo(-30, "note", "수업 전"), memo(999, "note", "수업 뒤")]}
        w = tr.recording_windows(s)[0]
        entries = tr.window_entries(s, w)
        self.assertEqual([e[0] for e in entries], [0, 1, 60, 75, 150])
        self.assertNotIn("수업 전", [e[2] for e in entries])
        self.assertNotIn("수업 뒤", [e[2] for e in entries])

    def test_memo_without_at_is_skipped(self):
        s = {"memos": [memo(0, "sys", "수업 시작"), {"kind": "note", "text": "시각 없음", "t": "01:00"}, "깨진 줄"]}
        entries = tr.window_entries(s, tr.recording_windows(s)[0])
        self.assertEqual([e[2] for e in entries], ["수업 시작"])


class AnalyzeTests(unittest.TestCase):
    def entries(self):
        s = {"memos": MEMOS}
        return tr.window_entries(s, tr.recording_windows(s)[0])

    def test_analysis_numbers(self):
        r = tr.analyze(SEGMENTS, self.entries(), total_sec=150)
        self.assertEqual(r["lines"], 3)
        self.assertEqual(r["questions"], 2)
        self.assertEqual(r["speech_sec"], 27)
        self.assertAlmostEqual(r["speech_ratio"], 27 / 150)
        self.assertIsNone(r["teacher_ratio"])  # 화자 구분 없음 → 확인 필요
        d, a = r["steps"]
        self.assertEqual((d["name"], d["start"], d["minutes"], d["lines"], d["questions"]), ("도입", 1, 1.0, 1, 0))
        self.assertEqual((a["name"], a["start"], a["minutes"], a["lines"], a["questions"]), ("활동", 60, 1.5, 2, 2))

    def test_total_falls_back_to_last_segment(self):
        self.assertEqual(tr.analyze(SEGMENTS, [])["total_sec"], 140)

    def test_teacher_ratio_only_with_speaker_labels(self):
        segs = [{"start": 0, "end": 30, "text": "가", "speaker": "T"}, {"start": 30, "end": 40, "text": "나", "speaker": "S1"}]
        self.assertAlmostEqual(tr.analyze(segs, [], teacher_label="T")["teacher_ratio"], 0.75)
        self.assertIsNone(tr.analyze(segs, [], teacher_label=None)["teacher_ratio"])
        self.assertIsNone(tr.analyze(SEGMENTS, [], teacher_label="T")["teacher_ratio"])

    def test_empty_and_blank_segments(self):
        r = tr.analyze([{"start": 0, "end": 5, "text": "  "}, "깨짐"], [])
        self.assertEqual((r["lines"], r["questions"], r["speech_ratio"]), (0, 0, None))

    def test_merged_lines_sorted_memo_first_on_tie(self):
        lines = tr.merged_lines([{"start": 60, "end": 65, "text": "시작해요"}], [(60, "step", "단계: 활동"), (10, "fix", "메모")])
        self.assertEqual(lines, ["[00:10] 🔧 메모", "[01:00] ▶ 단계: 활동", "[01:00] 시작해요"])


class ProcessTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        self.day = self.root / DAY
        self.day.mkdir()
        (self.day / REC).write_bytes(b"fake")
        session = {"subject": "국어", "rec_files": [REC], "memos": MEMOS}
        (self.day / "3교시_국어.json").write_text(json.dumps(session, ensure_ascii=False), encoding="utf-8")
        self.calls = []

    def fake(self, path):
        self.calls.append(path.name)
        return SEGMENTS

    def test_full_flow_writes_json_and_md(self):
        res = tr.process_recording(self.day / REC, self.fake)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["lines"], 3)
        self.assertEqual(res["notes"], [])
        saved = json.loads((self.day / (REC[:-5] + ".transcript.json")).read_text(encoding="utf-8"))
        self.assertEqual(len(saved["segments"]), 3)
        md = (self.day / (REC[:-5] + ".transcript.md")).read_text(encoding="utf-8")
        self.assertIn("[01:10] 주인공은 왜 그랬을까요?", md)
        self.assertIn("[01:15] 🔧 질문이 어려웠음", md)
        self.assertIn("| 활동 | 01:00 | 1.5 | 2 | 2 |", md)
        self.assertIn("교사 말 비율: 확인 필요", md)
        self.assertIn("녹음 길이: 02:30", md)

    def test_existing_transcript_not_redone_unless_asked(self):
        tr.process_recording(self.day / REC, self.fake)
        tr.process_recording(self.day / REC, self.fake)
        self.assertEqual(len(self.calls), 1)
        tr.process_recording(self.day / REC, self.fake, redo=True)
        self.assertEqual(len(self.calls), 2)

    def test_no_transcriber_and_no_text_is_missing(self):
        res = tr.process_recording(self.day / REC, None)
        self.assertEqual(res["status"], "missing")
        self.assertFalse((self.day / (REC[:-5] + ".transcript.md")).exists())

    def test_no_transcriber_uses_existing_text(self):
        tr.process_recording(self.day / REC, self.fake)
        res = tr.process_recording(self.day / REC, None)
        self.assertEqual((res["status"], res["lines"]), ("ok", 3))

    def test_recording_without_session_still_gets_text_and_note(self):
        (self.day / "3교시_국어.json").unlink()
        res = tr.process_recording(self.day / REC, self.fake)
        self.assertEqual(res["status"], "ok")
        self.assertTrue(any("rec_files" in n for n in res["notes"]))
        self.assertTrue((self.day / (REC[:-5] + ".transcript.md")).exists())

    def test_session_without_steps_notes_it(self):
        session = {"rec_files": [REC], "memos": [memo(0, "sys", "수업 시작"), memo(100, "sys", "수업 마침")]}
        (self.day / "3교시_국어.json").write_text(json.dumps(session), encoding="utf-8")
        res = tr.process_recording(self.day / REC, self.fake)
        self.assertTrue(any("단계" in n for n in res["notes"]))

    def test_broken_transcript_json_is_redone(self):
        (self.day / (REC[:-5] + ".transcript.json")).write_text("{깨짐", encoding="utf-8")
        res = tr.process_recording(self.day / REC, self.fake)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(len(self.calls), 1)

    def test_find_recordings_filters_period_and_extension(self):
        (self.day / "4교시_수학_111111.webm").write_bytes(b"x")
        (self.day / "3교시_국어.json").touch()
        (self.day / "메모.txt").touch()
        self.assertEqual([p.name for p in tr.find_recordings(self.day)], [REC, "4교시_수학_111111.webm"])
        self.assertEqual([p.name for p in tr.find_recordings(self.day, 4)], ["4교시_수학_111111.webm"])
        self.assertEqual(tr.find_recordings(self.root / "없는날"), [])

    def test_find_session_skips_transcript_json(self):
        tr.process_recording(self.day / REC, self.fake)
        self.assertEqual(tr.find_session(self.day, REC)["subject"], "국어")
        self.assertIsNone(tr.find_session(self.day, "없음.webm"))


class RunTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        day = self.root / DAY
        day.mkdir()
        (day / REC).write_bytes(b"fake")

    def test_whisper_missing_gives_install_help(self):
        with mock.patch.dict(sys.modules, {"faster_whisper": None}):
            results, unavailable = tr.run(DAY, self.root)
        self.assertIn("pip install faster-whisper", unavailable)
        self.assertEqual(results[0][1]["status"], "missing")

    def test_whisper_missing_still_analyzes_existing_text(self):
        (self.root / DAY / (REC[:-5] + ".transcript.json")).write_text(json.dumps({"segments": SEGMENTS}), encoding="utf-8")
        with mock.patch.dict(sys.modules, {"faster_whisper": None}):
            results, unavailable = tr.run(DAY, self.root)
        self.assertIsNone(unavailable)
        self.assertEqual(results[0][1]["status"], "ok")

    def test_load_transcriber_raises_unavailable(self):
        with mock.patch.dict(sys.modules, {"faster_whisper": None}):
            with self.assertRaises(tr.Unavailable):
                tr.load_transcriber()

    def test_run_with_fake_transcriber(self):
        results, unavailable = tr.run(DAY, self.root, transcriber=lambda p: SEGMENTS)
        self.assertIsNone(unavailable)
        self.assertEqual(results[0][1]["lines"], 3)

    def test_run_rejects_bad_date(self):
        with self.assertRaises(ValueError):
            tr.run("내일", self.root)

    def test_main_prints_counts_not_content(self):
        data = self.root / "data"
        day = data / "teacherlesson-assistant" / "sessions" / DAY
        day.mkdir(parents=True)
        (day / REC).write_bytes(b"fake")
        (day / (REC[:-5] + ".transcript.json")).write_text(json.dumps({"segments": SEGMENTS}), encoding="utf-8")
        out = io.StringIO()
        with mock.patch.dict("os.environ", {"MY_SKILLS_DATA_DIR": str(data)}), \
                mock.patch.object(sys, "argv", ["transcribe.py", "--date", DAY, "--no-transcribe"]), \
                contextlib.redirect_stdout(out):
            code = tr.main()
        self.assertEqual(code, 0)
        self.assertIn("조각 3개", out.getvalue())
        self.assertNotIn("주인공", out.getvalue())
        self.assertTrue((day / (REC[:-5] + ".transcript.md")).is_file())

    def test_main_bad_date_and_no_recordings(self):
        with mock.patch.dict("os.environ", {"MY_SKILLS_DATA_DIR": str(self.root / "d2")}):
            for argv, want in ((["--date", "내일"], 2), (["--date", DAY], 0)):
                with mock.patch.object(sys, "argv", ["transcribe.py", *argv]), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(tr.main(), want)


if __name__ == "__main__":
    unittest.main()
