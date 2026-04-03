import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

import map_general_guides_to_sheet
from sheet_uploader.core import REPLACE_APPEND, REPLACE_SUBJECTS


class MapGeneralGuidesToSheetTests(unittest.TestCase):
    def test_build_subject_config_uses_preset_defaults(self):
        config = map_general_guides_to_sheet.build_subject_config("사회")

        self.assertEqual(config["subject_name"], "사회")
        self.assertEqual(config["kind"], "general")
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

        self.assertEqual(
            [config["subject_name"] for config in configs],
            [
                subject_name
                for subject_name in map_general_guides_to_sheet.SUBJECT_ORDER
                if subject_name in map_general_guides_to_sheet.SUBJECT_PRESETS
            ],
        )

    def test_choose_configs_interactively_accepts_all(self):
        configs = map_general_guides_to_sheet.choose_configs_interactively(
            input_fn=lambda _prompt: "all"
        )

        self.assertEqual(
            [config["subject_name"] for config in configs],
            [
                subject_name
                for subject_name in map_general_guides_to_sheet.SUBJECT_ORDER
                if subject_name in map_general_guides_to_sheet.SUBJECT_PRESETS
            ],
        )

    def test_choose_configs_interactively_returns_auto_detected(self):
        fake_configs = [map_general_guides_to_sheet.build_subject_config("국어")]

        with patch.object(
            map_general_guides_to_sheet,
            "detect_available_subject_configs",
            return_value=fake_configs,
        ):
            configs = map_general_guides_to_sheet.choose_configs_interactively(
                input_fn=lambda _prompt: "auto"
            )

        self.assertEqual(configs, fake_configs)

    def test_confirm_upload_action_defaults_to_replace_subjects(self):
        answers = iter(["", ""])

        result = map_general_guides_to_sheet.confirm_upload_action(
            input_fn=lambda _prompt: next(answers),
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result, (True, False, REPLACE_SUBJECTS))

    def test_confirm_upload_action_supports_append_with_cleanup(self):
        answers = iter(["", "1", "y"])

        result = map_general_guides_to_sheet.confirm_upload_action(
            input_fn=lambda _prompt: next(answers),
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result, (True, True, REPLACE_APPEND))

    def test_detect_available_subject_configs_keeps_subject_order(self):
        def fake_has_material(config):
            return config["subject_name"] in {"국어", "수학", "미술"}

        with patch.object(
            map_general_guides_to_sheet,
            "subject_has_guide_material",
            side_effect=fake_has_material,
        ):
            configs = map_general_guides_to_sheet.detect_available_subject_configs()

        self.assertEqual(
            [config["subject_name"] for config in configs],
            ["국어", "수학", "미술"],
        )

    def test_generate_rows_for_configs_aggregates_special_and_general_subjects(self):
        configs = [
            map_general_guides_to_sheet.build_subject_config("국어"),
            map_general_guides_to_sheet.build_subject_config("사회"),
        ]

        with patch.object(
            map_general_guides_to_sheet,
            "generate_korean_data",
            return_value=[{"과목": "국어", "대단원": "국어 단원", "차시": "1", "수업내용": "국어 내용"}],
        ), patch.object(
            map_general_guides_to_sheet,
            "generate_general_data",
            return_value=[{"과목": "사회", "대단원": "사회 단원", "차시": "1", "수업내용": "사회 내용"}],
        ):
            rows, summaries = map_general_guides_to_sheet.generate_rows_for_configs(configs)

        self.assertEqual(len(rows), 2)
        self.assertEqual([row["과목"] for row in rows], ["국어", "사회"])
        self.assertEqual([summary[0]["subject_name"] for summary in summaries], ["국어", "사회"])

    def test_write_generation_artifacts_writes_latest_snapshot(self):
        configs = [
            map_general_guides_to_sheet.build_subject_config("국어"),
            map_general_guides_to_sheet.build_subject_config("수학"),
        ]
        summaries = [
            (configs[0], [{"과목": "국어", "대단원": "국어 단원", "차시": "1", "수업내용": "국어 내용"}]),
            (configs[1], [{"과목": "수학", "대단원": "수학 단원", "차시": "1", "수업내용": "수학 내용"}]),
        ]
        rows = [row for _config, subject_rows in summaries for row in subject_rows]

        workspace_dir = Path(__file__).resolve().parents[1]
        tmp_dir = workspace_dir / "_test_generated_rows"
        shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            with patch.object(
                map_general_guides_to_sheet,
                "GENERATED_ROWS_DIR",
                tmp_dir,
            ):
                artifact_dir = map_general_guides_to_sheet.write_generation_artifacts(summaries, rows)

            latest_rows_path = tmp_dir / "latest_all_rows.json"
            self.assertTrue(artifact_dir.exists())
            self.assertTrue(latest_rows_path.exists())
            payload = json.loads(latest_rows_path.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        self.assertEqual(payload["total_row_count"], 2)
        self.assertEqual([row["과목"] for row in payload["rows"]], ["국어", "수학"])


if __name__ == "__main__":
    unittest.main()
