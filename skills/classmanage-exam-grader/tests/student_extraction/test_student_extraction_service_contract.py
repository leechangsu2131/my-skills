from packages.student_extraction import service


def test_legacy_ocr_extractor_reexports_student_extraction_service() -> None:
    import ocr_extractor

    assert ocr_extractor.extract_answers is service.extract_answers
    assert ocr_extractor.extract_batch is service.extract_batch
    assert ocr_extractor.load_config is service.load_config


def test_webapp_pipeline_uses_student_extraction_service() -> None:
    from webapp.services import pipeline

    assert pipeline.extract_answers is service.extract_answers
