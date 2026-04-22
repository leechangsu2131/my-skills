from apps.cli import grade_exam as cli_entry
from apps.web import main as web_entry


def test_web_app_entrypoint_matches_existing_webapp_module() -> None:
    import webapp.main

    assert web_entry.create_app is webapp.main.create_app
    assert web_entry.app is webapp.main.app


def test_cli_entrypoint_matches_existing_grade_exam_module() -> None:
    import grade_exam

    assert cli_entry.main is grade_exam.main
