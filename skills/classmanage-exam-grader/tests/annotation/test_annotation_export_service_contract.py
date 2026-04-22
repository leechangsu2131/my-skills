from packages.annotation import service as annotation_service
from packages.export import service as export_service


def test_legacy_output_modules_match_package_services() -> None:
    import html_reporter
    import pdf_annotator

    assert pdf_annotator.annotate_pdf is annotation_service.annotate_pdf
    assert pdf_annotator.annotate_batch is annotation_service.annotate_batch
    assert html_reporter.generate_dashboard is export_service.generate_dashboard


def test_pipeline_and_cli_use_output_package_services() -> None:
    import grade_exam
    from webapp.services import pipeline

    assert pipeline.annotate_pdf is annotation_service.annotate_pdf
    assert grade_exam.annotate_batch is annotation_service.annotate_batch
    assert grade_exam.generate_dashboard is export_service.generate_dashboard
