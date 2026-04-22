from packages.answer_key_extraction import service


def test_legacy_answer_key_parser_reexports_service() -> None:
    import answer_key_parser

    assert answer_key_parser.parse_answer_key_pdf is service.parse_answer_key_pdf
    assert answer_key_parser.load_answer_key_json is service.load_answer_key_json
    assert answer_key_parser.save_answer_key is service.save_answer_key


def test_webapp_pipeline_uses_answer_key_extraction_service() -> None:
    from webapp.services import pipeline

    assert pipeline.parse_answer_key_pdf is service.parse_answer_key_pdf
