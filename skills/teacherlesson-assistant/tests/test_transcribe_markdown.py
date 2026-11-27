"""transcribe.build_markdown(받아쓰기 결과 → 마크다운 글) 시험 (S1).

    python -m unittest discover -s tests -v      (skills/teacherlesson-assistant 폴더에서)

가짜 받아쓰기 조각·메모만 쓴다(학생 이름은 '학생A', faster-whisper·녹음 파일은 안 씀).
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import transcribe as tr  # noqa: E402

SEGMENTS = [
    {"start": 5.0, "end": 12.0, "text": "오늘은 이야기를 읽어 볼 거예요."},
    {"start": 70.0, "end": 80.0, "text": "주인공은 왜 그랬을까요? 학생A가 말해 볼까요?"},
]
ENTRIES = [(0.0, "step", "단계: 도입"), (60.0, "student", "학생A 발표"), (70.0, "note", "메모 하나")]


def build(segments=SEGMENTS, entries=ENTRIES, total_sec=120, teacher_label=None, notes=()):
    result = tr.analyze(segments, entries, total_sec=total_sec, teacher_label=teacher_label)
    return tr.build_markdown("3교시_국어.webm", segments, entries, result, list(notes)), result


class BuildMarkdownTest(unittest.TestCase):
    def test_title_and_sections_are_in_order(self):
        md, _ = build()
        lines = md.split("\n")
        self.assertEqual(lines[0], "# 수업 녹음 받아쓰기 — 3교시_국어.webm")
        order = [md.index(h) for h in ("## 분석", "### 단계별 시간", "## 받아쓴 글 (메모 포함)")]
        self.assertEqual(order, sorted(order))

    def test_no_notes_means_no_check_section(self):
        md, _ = build()
        self.assertNotIn("## 확인 필요", md)

    def test_notes_are_listed_first_as_bullets(self):
        md, _ = build(notes=["받아쓰기가 일부 비었어요", "메모 시각이 겹쳐요"])
        self.assertIn("## 확인 필요\n- 받아쓰기가 일부 비었어요\n- 메모 시각이 겹쳐요\n", md)
        self.assertLess(md.index("## 확인 필요"), md.index("## 분석"))

    def test_analysis_numbers(self):
        md, result = build()
        self.assertIn("- 녹음 길이: 02:00", md)
        self.assertIn("- 말소리가 있는 시간: 00:17 (14%) — 교사·학생 구분 없음", md)
        self.assertIn("- 물음표 문장: 2개 (추정", md)
        self.assertEqual(result["questions"], 2)

    def test_teacher_ratio_is_unknown_without_speaker_labels(self):
        md, _ = build()
        self.assertIn("- 교사 말 비율: 확인 필요", md)

    def test_teacher_ratio_is_shown_with_speaker_labels(self):
        segs = [{"start": 0, "end": 30, "text": "설명해요.", "speaker": "T"},
                {"start": 30, "end": 40, "text": "대답해요.", "speaker": "S"}]
        md, _ = build(segs, [], total_sec=40, teacher_label="T")
        self.assertIn("- 교사 말 비율: 75%", md)
        self.assertNotIn("확인 필요", md)

    def test_step_table_rows(self):
        md, _ = build()
        self.assertIn("| 단계 | 시작 | 걸린 시간(분) | 말 줄 수 | 물음표 문장 |", md)
        self.assertIn("| 도입 | 00:00 | 2.0 | 2 | 2 |", md)

    def test_no_steps_means_no_table(self):
        md, _ = build(entries=[(60.0, "note", "메모만")])
        self.assertNotIn("### 단계별 시간", md)

    def test_transcript_lines_are_time_ordered_with_memo_first_on_same_second(self):
        md, _ = build()
        body = md.split("## 받아쓴 글 (메모 포함)\n\n", 1)[1].strip().split("\n")
        self.assertEqual(body, [
            "[00:00] ▶ 단계: 도입",
            "[00:05] 오늘은 이야기를 읽어 볼 거예요.",
            "[01:00] 🙋 학생A 발표",
            "[01:10] 📝 메모 하나",            # 같은 초(70)에서는 메모가 받아쓴 글보다 먼저
            "[01:10] 주인공은 왜 그랬을까요? 학생A가 말해 볼까요?",
        ])

    def test_empty_recording_still_makes_a_valid_document(self):
        md, result = build([], [], total_sec=None)
        self.assertIsNone(result["speech_ratio"])
        self.assertIn("- 녹음 길이: 00:00", md)
        self.assertNotIn("말소리가 있는 시간", md)
        self.assertTrue(md.endswith("## 받아쓴 글 (메모 포함)\n\n"))


if __name__ == "__main__":
    unittest.main()
