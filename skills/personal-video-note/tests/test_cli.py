from lecturecapture.cli import build_parser


def test_local_video_is_primary_cli_path_and_whisper_defaults_to_large_v3():
    args = build_parser().parse_args(["run", "lecture.mp4"])
    assert args.out is None
    assert args.subtitle is None
    assert args.transcribe is None
    assert args.whisper_model == "large-v3"
    assert args.source_url is None


def test_no_transcribe_can_be_selected_explicitly():
    args = build_parser().parse_args(["run", "lecture.mp4", "--no-transcribe"])
    assert args.transcribe is False


def test_transcript_export_and_initial_prompt_options():
    args = build_parser().parse_args([
        "run", "lecture.mp4", "--export-transcript",
        "--initial-prompt", "초등 교육, 형성평가, 기초학력",
    ])
    assert args.export_transcript is True
    assert args.initial_prompt == "초등 교육, 형성평가, 기초학력"


def test_hotwords_option():
    from lecturecapture.cli import build_parser

    args = build_parser().parse_args(["run", "lecture.mp4", "--hotwords", "교육연극, 행복교실"])
    assert args.hotwords == "교육연극, 행복교실"


def test_reference_materials_can_be_repeated():
    args = build_parser().parse_args([
        "run", "lecture.mp4", "--reference", "guide.hwpx", "--reference", "terms.pdf",
    ])
    assert [str(path) for path in args.reference] == ["guide.hwpx", "terms.pdf"]
