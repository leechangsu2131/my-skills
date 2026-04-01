import unittest
from unittest.mock import patch

import map_general_guides_to_sheet


class MapGeneralGuidesToSheetTests(unittest.TestCase):
    def test_build_subject_config_uses_preset_defaults(self):
        config = map_general_guides_to_sheet.build_subject_config("사회")

        self.assertEqual(config["subject_name"], "사회")
        self.assertEqual(config["prefix"], "사회")
        self.assertEqual(config["grade_str"], "3-1")
        self.assertEqual(config["max_unit"], 4)
        self.assertTrue(config["disable_heuristic"])

    def test_build_subject_config_allows_manual_override(self):
        config = map_general_guides_to_sheet.build_subject_config(
            "미술",
            prefix="초등학교 미술",
            grade_str="4",
            max_unit=9,
            disable_heuristic=True,
        )

        self.assertEqual(config["prefix"], "초등학교 미술")
        self.assertEqual(config["grade_str"], "4")
        self.assertEqual(config["max_unit"], 9)
        self.assertTrue(config["disable_heuristic"])

    def test_resolve_subject_configs_supports_all_presets(self):
        configs = map_general_guides_to_sheet.resolve_subject_configs(use_all_presets=True)

        self.assertEqual([config["subject_name"] for config in configs], list(map_general_guides_to_sheet.SUBJECT_PRESETS.keys()))

    def test_choose_configs_interactively_accepts_all(self):
        configs = map_general_guides_to_sheet.choose_configs_interactively(
            input_fn=lambda _prompt: "all"
        )

        self.assertEqual(
            [config["subject_name"] for config in configs],
            list(map_general_guides_to_sheet.SUBJECT_PRESETS.keys()),
        )

    def test_choose_configs_interactively_returns_empty_on_blank(self):
        configs = map_general_guides_to_sheet.choose_configs_interactively(
            input_fn=lambda _prompt: ""
        )

        self.assertEqual(configs, [])

    def test_confirm_upload_action_defaults_to_upload_without_cleanup(self):
        answers = iter(["", ""])

        result = map_general_guides_to_sheet.confirm_upload_action(
            input_fn=lambda _prompt: next(answers),
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result, (True, False))

    def test_confirm_upload_action_can_cancel_upload(self):
        result = map_general_guides_to_sheet.confirm_upload_action(
            input_fn=lambda _prompt: "n",
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result, (False, False))

    def test_confirm_upload_action_can_enable_cleanup(self):
        answers = iter(["", "y"])

        result = map_general_guides_to_sheet.confirm_upload_action(
            input_fn=lambda _prompt: next(answers),
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result, (True, True))

    def test_generate_rows_for_configs_aggregates_all_subjects(self):
        configs = [
            {"subject_name": "사회", "prefix": "사회", "grade_str": "3-1", "max_unit": 4, "disable_heuristic": True},
            {"subject_name": "과학", "prefix": "과학", "grade_str": "3-1", "max_unit": 5, "disable_heuristic": False},
        ]

        def fake_generate_general_data(subject_name, prefix, max_unit=5, disable_heuristic=False, grade_str="3-1"):
            return [
                {
                    "과목": subject_name,
                    "대단원": f"{subject_name} 단원",
                    "차시": "1",
                    "수업내용": f"{subject_name} 내용",
                }
            ]

        with patch.object(map_general_guides_to_sheet, "generate_general_data", side_effect=fake_generate_general_data):
            rows, summaries = map_general_guides_to_sheet.generate_rows_for_configs(configs)

        self.assertEqual(len(rows), 2)
        self.assertEqual([row["과목"] for row in rows], ["사회", "과학"])
        self.assertEqual([summary[0]["subject_name"] for summary in summaries], ["사회", "과학"])


if __name__ == "__main__":
    unittest.main()
