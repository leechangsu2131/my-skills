import unittest

import social_class_helper


class FakeSwitchTo:
    def __init__(self, driver):
        self.driver = driver

    def window(self, handle):
        if handle in self.driver.bad_handles:
            raise RuntimeError("closed window")
        self.driver.current_handle = handle


class FakeDriver:
    def __init__(self):
        self.window_handles = ["closed", "live"]
        self.bad_handles = {"closed"}
        self.current_handle = None
        self.switch_to = FakeSwitchTo(self)
        self.urls = {"live": "https://www.i-scream.co.kr/user/subject/SubjectChasiList.do#none"}

    def execute_script(self, _script):
        if self.current_handle in self.bad_handles or self.current_handle is None:
            raise RuntimeError("window is not available")
        return "complete"

    @property
    def current_url(self):
        if self.current_handle in self.bad_handles or self.current_handle is None:
            raise RuntimeError("window is not available")
        return self.urls.get(self.current_handle, "")


class SocialClassHelperTests(unittest.TestCase):
    def test_detect_site_kind(self):
        self.assertEqual(
            social_class_helper.detect_site_kind(
                "https://www.i-scream.co.kr/user/subject/SubjectChasiList.do#none"
            ),
            "iscream",
        )
        self.assertEqual(
            social_class_helper.detect_site_kind("https://ele.douclass.com/textbooks/30050/518"),
            "douclass",
        )

    def test_parse_env_lines_ignores_comments_and_quotes(self):
        values = social_class_helper.parse_env_lines(
            [
                "# comment",
                "SOCIAL_CLASS_BASE_URL='https://example.com'",
                'SOCIAL_CLASS_LABEL="사회 수업 도우미"',
                "INVALID_LINE",
            ]
        )

        self.assertEqual(values["SOCIAL_CLASS_BASE_URL"], "https://example.com")
        self.assertEqual(values["SOCIAL_CLASS_LABEL"], "사회 수업 도우미")
        self.assertNotIn("INVALID_LINE", values)

    def test_parse_csv_splits_and_trims(self):
        result = social_class_helper.parse_csv("PPT, 수업자료,  활동지  ,")

        self.assertEqual(result, ["PPT", "수업자료", "활동지"])

    def test_unit_matches_by_number(self):
        self.assertTrue(social_class_helper.unit_matches("1. 우리 지역의 모습", "1단원"))
        self.assertFalse(social_class_helper.unit_matches("2. 민주주의와 시민", "1단원"))

    def test_clean_iscream_unit_title_removes_noise(self):
        result = social_class_helper.clean_iscream_unit_title(
            "1. 우리가 사는 곳의 여러 장소 사회 골든벨 Quiz사회 알짜정리 학습지 교과서PDF 공유자료실"
        )

        self.assertEqual(result, "1. 우리가 사는 곳의 여러 장소")

    def test_lesson_matches_exact_title_or_lesson_number(self):
        title = "[3~4차시] 우리 고장의 위치 알아보기"

        self.assertTrue(social_class_helper.lesson_matches(title, title))
        self.assertTrue(social_class_helper.lesson_matches(title, "3차시"))
        self.assertTrue(social_class_helper.lesson_matches(title, "위치 알아보기"))

    def test_resource_match_score_prefers_matching_keywords(self):
        score = social_class_helper.resource_match_score(
            "교수자료 PPT 다운로드",
            ["PPT", "활동지"],
        )

        self.assertGreater(score, 0)

    def test_switch_to_live_window_skips_closed_handle(self):
        driver = FakeDriver()

        result = social_class_helper.switch_to_live_window(driver)

        self.assertTrue(result)
        self.assertEqual(driver.current_handle, "live")


if __name__ == "__main__":
    unittest.main()
