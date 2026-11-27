"""💬 학생 대응 멘트 도우미 시험 (T106) — 문장 파일 모양, 교사 대답 합치기, 누른 횟수, 서버 경로, 주간 정리.

    python -m pytest tests/test_ment.py -v        (teacherlesson-assistant 폴더에서)

임시 폴더만 쓴다(실제 데이터 폴더의 ment_custom.json·ment_counts.json 은 건드리지 않음). 이름은 모두 가짜.
"""
import copy
import http.client
import json
import pathlib
import sys
import threading
import tempfile
import unittest
from datetime import date
from http.server import ThreadingHTTPServer

SKILL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL))
import assistant_server as app  # noqa: E402
import ment  # noqa: E402
import weekly_report as wr  # noqa: E402

REAL = json.loads((SKILL / "web" / "ment.json").read_text(encoding="utf-8"))


def situation(sid="noisy", **kw):
    base = {"id": sid, "icon": "🔊", "label": "떠들기", "said": "떠들어요", "answers": ["가", "나"],
            "principle": {"name": "원리", "note": "설명"}}
    base.update(kw)
    return base


class RealFileTest(unittest.TestCase):
    """저장소에 올라간 web/ment.json 자체를 본다."""

    def test_shape_is_valid(self):
        self.assertEqual(ment.check_shape(REAL), [])

    def test_at_least_12_situations_with_2_or_3_answers(self):
        self.assertGreaterEqual(len(REAL["situations"]), 12)
        for s in REAL["situations"]:
            self.assertIn(len(s["answers"]), (2, 3), s["id"])

    def test_required_situations_from_the_task_are_there(self):
        text = " ".join(s["label"] + s["said"] for s in REAL["situations"])
        for word in ("떠들", "못 해요", "거부", "다툼", "남 탓", "고자질", "자리", "장난", "울음", "무시", "늦게", "과제"):
            self.assertIn(word, text, word)

    def test_principles_cover_the_named_ones(self):
        text = " ".join(s["principle"]["name"] for s in REAL["situations"])
        for word in ("나-전달법", "감정 읽기", "선택권", "성장 마인드셋", "행동과 사람"):
            self.assertIn(word, text, word)

    def test_no_student_names_or_phone_like_text(self):
        import re
        raw = json.dumps(REAL, ensure_ascii=False)
        self.assertIsNone(re.search(r"\d{2,3}-\d{3,4}-\d{4}", raw))
        self.assertNotIn("학생A", raw)

    def test_ids_are_unique(self):
        ids = [s["id"] for s in REAL["situations"]]
        self.assertEqual(len(ids), len(set(ids)))


class CheckShapeTest(unittest.TestCase):
    def test_good_minimal(self):
        self.assertEqual(ment.check_shape({"situations": [situation()]}), [])

    def test_not_an_object_or_no_list(self):
        for bad in ([], None, "x", {"situations": "x"}, {}):
            self.assertTrue(ment.check_shape(bad), repr(bad))

    def test_each_kind_of_mistake_is_reported(self):
        cases = {
            "id 빈": situation(id=" "), "label 빈": situation(label=""), "said 없음": {k: v for k, v in situation().items() if k != "said"},
            "answers 1개": situation(answers=["가"]), "answers 4개": situation(answers=list("가나다라")),
            "answers 빈칸": situation(answers=["가", " "]), "principle 없음": situation(principle=None),
            "principle note 빈": situation(principle={"name": "원리", "note": ""}),
        }
        for name, item in cases.items():
            with self.subTest(name):
                self.assertTrue(ment.check_shape({"situations": [item]}), name)

    def test_duplicate_ids_and_non_object_entry(self):
        self.assertTrue(ment.check_shape({"situations": [situation(), situation()]}))
        self.assertTrue(ment.check_shape({"situations": ["x"]}))


class LoadAndCustomTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.situations = [situation("noisy"), situation("cry", label="울음")]
        self.custom = self.dir / "ment_custom.json"

    def test_load_situations_missing_or_broken_file_gives_empty(self):
        self.assertEqual(ment.load_situations(self.dir / "없음.json"), [])
        (self.dir / "broken.json").write_text("{깨짐", encoding="utf-8")
        self.assertEqual(ment.load_situations(self.dir / "broken.json"), [])
        (self.dir / "bad.json").write_text(json.dumps({"situations": [situation(answers=[])]}), encoding="utf-8")
        self.assertEqual(ment.load_situations(self.dir / "bad.json"), [])

    def test_read_custom_survives_broken_and_odd_shapes(self):
        self.assertEqual(ment.read_custom(self.custom), {})
        self.custom.write_text("[1,2]", encoding="utf-8")
        self.assertEqual(ment.read_custom(self.custom), {})
        self.custom.write_text(json.dumps({"noisy": ["가", 3, " ", "나"], "cry": "글"}), encoding="utf-8")  # 목록이 아닌 값은 버린다
        self.assertEqual(ment.read_custom(self.custom), {"noisy": ["가", "나"]})

    def test_with_custom_adds_list_and_ignores_unknown_situation(self):
        merged = ment.with_custom(self.situations, {"noisy": ["내 대답"], "없는상황": ["x"]})
        self.assertEqual(merged[0]["custom"], ["내 대답"])
        self.assertEqual(merged[1]["custom"], [])
        self.assertEqual(len(merged), 2)
        self.assertNotIn("custom", self.situations[0])  # 원본은 바꾸지 않는다

    def test_add_custom_saves_trimmed_text_and_reads_back(self):
        self.assertEqual(ment.add_custom(self.custom, self.situations, "noisy", "  내 대답  "), ["내 대답"])
        self.assertEqual(ment.add_custom(self.custom, self.situations, "noisy", "둘째"), ["내 대답", "둘째"])
        self.assertEqual(ment.read_custom(self.custom), {"noisy": ["내 대답", "둘째"]})

    def test_same_text_is_not_added_twice(self):
        ment.add_custom(self.custom, self.situations, "noisy", "같은 글")
        self.assertEqual(ment.add_custom(self.custom, self.situations, "noisy", "같은 글"), ["같은 글"])

    def test_add_custom_rejects_bad_input_and_writes_nothing(self):
        for situation_id, text in (("없는상황", "글"), ("noisy", ""), ("noisy", "   "), ("noisy", None), ("noisy", "가" * (ment.MAX_TEXT + 1))):
            with self.subTest(situation_id=situation_id, text=str(text)[:5]):
                with self.assertRaises(ValueError):
                    ment.add_custom(self.custom, self.situations, situation_id, text)
        self.assertFalse(self.custom.exists())

    def test_text_at_the_limit_is_accepted(self):
        self.assertEqual(len(ment.add_custom(self.custom, self.situations, "noisy", "가" * ment.MAX_TEXT)), 1)

    def test_per_situation_limit(self):
        for n in range(ment.MAX_CUSTOM_PER_SITUATION):
            ment.add_custom(self.custom, self.situations, "noisy", f"글{n}")
        with self.assertRaises(ValueError):
            ment.add_custom(self.custom, self.situations, "noisy", "하나 더")
        self.assertEqual(len(ment.read_custom(self.custom)["noisy"]), ment.MAX_CUSTOM_PER_SITUATION)
        ment.add_custom(self.custom, self.situations, "cry", "다른 상황은 따로 센다")

    def test_remove_custom(self):
        for text in ("가", "나", "다"):
            ment.add_custom(self.custom, self.situations, "noisy", text)
        self.assertEqual(ment.remove_custom(self.custom, self.situations, "noisy", 1), ["가", "다"])
        self.assertEqual(ment.read_custom(self.custom), {"noisy": ["가", "다"]})

    def test_removing_last_one_drops_the_situation_key(self):
        ment.add_custom(self.custom, self.situations, "noisy", "가")
        ment.remove_custom(self.custom, self.situations, "noisy", 0)
        self.assertEqual(ment.read_custom(self.custom), {})

    def test_remove_rejects_bad_index_and_situation(self):
        ment.add_custom(self.custom, self.situations, "noisy", "가")
        for situation_id, index in (("noisy", 1), ("noisy", -1), ("noisy", "0"), ("noisy", True), ("noisy", None), ("없는상황", 0), ("cry", 0)):
            with self.subTest(situation_id=situation_id, index=index):
                with self.assertRaises(ValueError):
                    ment.remove_custom(self.custom, self.situations, situation_id, index)
        self.assertEqual(ment.read_custom(self.custom), {"noisy": ["가"]})

    def test_concurrent_adds_do_not_lose_entries(self):
        threads = [threading.Thread(target=ment.add_custom, args=(self.custom, self.situations, "noisy", f"글{n}")) for n in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(ment.read_custom(self.custom)["noisy"]), 8)


class CountTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self._tmp.name) / "ment_counts.json"
        self.addCleanup(self._tmp.cleanup)
        self.situations = [situation("noisy"), situation("cry", label="울음")]

    def test_press_counts_per_day_and_situation(self):
        self.assertEqual(ment.press(self.path, self.situations, "noisy", "2026-11-23"), 1)
        self.assertEqual(ment.press(self.path, self.situations, "noisy", "2026-11-23"), 2)
        self.assertEqual(ment.press(self.path, self.situations, "cry", "2026-11-23"), 1)
        self.assertEqual(ment.press(self.path, self.situations, "noisy", "2026-11-24"), 1)
        self.assertEqual(ment.read_counts(self.path), {"2026-11-23": {"noisy": 2, "cry": 1}, "2026-11-24": {"noisy": 1}})

    def test_file_has_no_text_or_names_only_numbers(self):
        ment.press(self.path, self.situations, "noisy", "2026-11-23")
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(raw, {"2026-11-23": {"noisy": 1}})

    def test_bad_situation_or_date_is_refused_and_writes_nothing(self):
        for situation_id, day in (("없는상황", "2026-11-23"), ("noisy", "어제"), ("noisy", "2026-13-40")):
            with self.subTest(situation_id=situation_id, day=day):
                with self.assertRaises(ValueError):
                    ment.press(self.path, self.situations, situation_id, day)
        self.assertFalse(self.path.exists())

    def test_default_day_is_today(self):
        ment.press(self.path, self.situations, "noisy")
        self.assertIn(date.today().isoformat(), ment.read_counts(self.path))

    def test_read_counts_drops_odd_values(self):
        self.path.write_text(json.dumps({"2026-11-23": {"noisy": 2, "cry": "x", "a": -1, "b": True, "c": 0}, "x": 5}), encoding="utf-8")
        self.assertEqual(ment.read_counts(self.path), {"2026-11-23": {"noisy": 2}})
        self.path.write_text("[1]", encoding="utf-8")
        self.assertEqual(ment.read_counts(self.path), {})

    def test_week_counts_sums_monday_to_sunday_only(self):
        counts = {"2026-11-22": {"noisy": 9},  # 지난 주 일요일
                  "2026-11-23": {"noisy": 1, "cry": 1}, "2026-11-25": {"noisy": 2}, "2026-11-29": {"cry": 3},
                  "2026-11-30": {"noisy": 9}}  # 다음 주 월요일
        self.assertEqual(ment.week_counts(counts, date(2026, 11, 23)), {"noisy": 3, "cry": 4})

    def test_concurrent_presses_are_all_counted(self):
        threads = [threading.Thread(target=ment.press, args=(self.path, self.situations, "noisy", "2026-11-23")) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(ment.read_counts(self.path), {"2026-11-23": {"noisy": 10}})


class HttpTest(unittest.TestCase):
    """실제 서버 경로(/api/ment*)를 임시 폴더로 돌린다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)
        self._saved = (app.MENT_CUSTOM, app.MENT_COUNTS)
        app.MENT_CUSTOM, app.MENT_COUNTS = self.dir / "ment_custom.json", self.dir / "ment_counts.json"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        app.MENT_CUSTOM, app.MENT_COUNTS = self._saved
        self._tmp.cleanup()

    def call(self, method, path, payload=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        conn.request(method, path, data, {"Content-Type": "application/json", **(headers or {})})
        res = conn.getresponse()
        raw = res.read()
        return res.status, raw

    def post(self, path, payload, headers=None):
        status, raw = self.call("POST", path, payload, headers)
        return status, json.loads(raw.decode("utf-8"))

    def test_get_list_has_all_situations_with_empty_custom(self):
        status, data = self.post("/api/ment-custom", {"situation": "noisy", "text": "내 대답"})
        self.assertEqual(status, 200)
        status, raw = self.call("GET", "/api/ment")
        data = json.loads(raw.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(len(data["situations"]), len(REAL["situations"]))
        noisy = next(s for s in data["situations"] if s["id"] == "noisy")
        self.assertEqual(noisy["custom"], ["내 대답"])
        self.assertTrue(all(s["custom"] == [] for s in data["situations"] if s["id"] != "noisy"))

    def test_static_files_are_served(self):
        status, raw = self.call("GET", "/ment.js")
        self.assertEqual(status, 200)
        self.assertIn(b"initMent" if b"initMent" in raw else b"mentFocusActive", raw)

    def test_add_then_delete_custom(self):
        status, data = self.post("/api/ment-custom", {"situation": "cry", "text": "함께 있어 줄게요"})
        self.assertEqual((status, data["custom"]), (200, ["함께 있어 줄게요"]))
        status, data = self.post("/api/ment-custom", {"situation": "cry", "delete": 0})
        self.assertEqual((status, data["custom"]), (200, []))
        self.assertEqual(ment.read_custom(app.MENT_CUSTOM), {})

    def test_bad_custom_is_400_with_korean_message(self):
        for payload in ({"situation": "없음", "text": "글"}, {"situation": "cry", "text": ""}, {"situation": "cry", "delete": 3}):
            status, data = self.post("/api/ment-custom", payload)
            self.assertEqual(status, 400, payload)
            self.assertEqual(data["status"], "error")
            self.assertTrue(data["message"])

    def test_count_route_counts_today_and_refuses_unknown(self):
        status, data = self.post("/api/ment-count", {"situation": "noisy"})
        self.assertEqual((status, data["count"]), (200, 1))
        status, data = self.post("/api/ment-count", {"situation": "noisy"})
        self.assertEqual(data["count"], 2)
        status, _ = self.post("/api/ment-count", {"situation": "없는상황"})
        self.assertEqual(status, 400)
        self.assertEqual(ment.read_counts(app.MENT_COUNTS), {date.today().isoformat(): {"noisy": 2}})

    def test_other_site_origin_is_refused(self):
        status, _ = self.post("/api/ment-count", {"situation": "noisy"}, {"Origin": "https://evil.example"})
        self.assertEqual(status, 403)
        status, _ = self.post("/api/ment-custom", {"situation": "noisy", "text": "x"}, {"Origin": "https://evil.example"})
        self.assertEqual(status, 403)
        self.assertFalse(app.MENT_COUNTS.exists() or app.MENT_CUSTOM.exists())


class WeeklyReportTest(unittest.TestCase):
    def test_counts_section_lists_labels_most_first_without_names(self):
        monday = date(2026, 11, 23)
        text = wr.build_report([], monday, set(), {}, [("울음", 1), ("떠들기", 3)])
        self.assertIn("## 💬 상황별 대응 멘트 사용 횟수", text)
        tail = text.split("## 💬 상황별 대응 멘트 사용 횟수")[1]
        self.assertLess(tail.index("떠들기: 3번"), tail.index("울음: 1번"))

    def test_empty_week_says_so(self):
        text = wr.build_report([], date(2026, 11, 23), set(), {}, [])
        self.assertIn("이번 주에 누른 기록이 없습니다.", text)
        self.assertIn("이번 주에 누른 기록이 없습니다.", wr.build_report([], date(2026, 11, 23), set(), {}))

    def test_section_adds_no_student_sections(self):
        text = wr.build_report([], date(2026, 11, 23), set(), {}, [("떠들기", 3)])
        self.assertEqual(text.split("## 🙋 학생별 발표 메모")[1].count("\n### "), 0)

    def test_make_report_reads_counts_file_for_that_week_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = pathlib.Path(tmp)
            (data / "sessions").mkdir()
            (data / "ment_counts.json").write_text(json.dumps({
                "2026-11-24": {"noisy": 2}, "2026-11-30": {"cry": 5}}), encoding="utf-8")
            path, _, _ = wr.make_report(data, date(2026, 11, 26))
            text = path.read_text(encoding="utf-8")
        self.assertIn("떠들기: 2번", text)
        self.assertNotIn("울음", text)

    def test_unknown_situation_id_is_shown_as_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = pathlib.Path(tmp)
            (data / "sessions").mkdir()
            (data / "ment_counts.json").write_text(json.dumps({"2026-11-24": {"옛상황": 1}}), encoding="utf-8")
            path, _, _ = wr.make_report(data, date(2026, 11, 26))
            self.assertIn("옛상황: 1번", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
