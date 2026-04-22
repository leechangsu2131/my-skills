from packages.grading import service


def test_legacy_grader_modules_reexport_grading_service() -> None:
    import analysis_merger
    import grader

    assert grader.grade_student is service.grade_student
    assert grader.load_config is service.load_config
    assert analysis_merger.merge_analysis is service.merge_analysis


def test_webapp_pipeline_uses_grading_service() -> None:
    from webapp.services import pipeline

    assert pipeline.grade_student is service.grade_student
    assert pipeline.load_config is service.load_config
    assert pipeline.merge_analysis is service.merge_analysis
