from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from .crop import parse_crop, select_crop
from .ingest import download_authorized_video, youtube_video_id
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lecturecapture", description="강의 영상 슬라이드 캡처 초안")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="로컬 영상에서 슬라이드를 추출하고 HTML 보고서를 생성합니다.")
    run.add_argument("video", type=Path, help="사용 권한이 있는 로컬 영상 파일")
    run.add_argument("--out", type=Path, help="프로젝트 결과 폴더(생략하면 영상 옆에 <영상이름>_LectureCapture 생성)")
    run.add_argument("--crop", type=str, help="화면 영역 x,y,w,h. 생략하면 첫 프레임에서 직접 선택")
    run.add_argument("--interval", type=float, default=0.75, help="프레임 샘플 간격(초, 기본 0.75)")
    run.add_argument("--change-threshold", type=float, default=1.5, help="기준 프레임 대비 변화한 픽셀 비율(%%, 기본 1.5). 텍스트 슬라이드 전환은 보통 2%% 안팎")
    run.add_argument("--min-stable", type=float, default=2.5, help="슬라이드 최소 지속 시간(초, 기본 2.5). 디졸브 같은 전환 중간 화면을 걸러내는 기준도 겸함")
    run.add_argument("--pixel-delta", type=int, default=30, help="픽셀이 변했다고 보는 밝기 차이(0~255, 기본 30)")
    run.add_argument("--removal-threshold", type=float, default=0.25, help="기존 슬라이드 내용이 사라진 픽셀 비율(%%, 기본 0.25). 글머리표 추가는 무시하고 슬라이드 교체는 잡아냄")
    run.add_argument("--diagnose", action="store_true", help="샘플별 변화율을 diagnostics.csv로 저장(임계값 조정용)")
    run.add_argument("--subtitle", type=Path, help="선택: SRT/VTT 자막 파일. 지정하면 음성 전사보다 우선")
    transcribe_group = run.add_mutually_exclusive_group()
    transcribe_group.add_argument("--transcribe", dest="transcribe", action="store_true", help="자막 파일이 있어도 faster-whisper 전사를 사용")
    transcribe_group.add_argument("--no-transcribe", dest="transcribe", action="store_false", help="자동 음성 전사를 사용하지 않음")
    run.set_defaults(transcribe=None)
    run.add_argument("--whisper-model", default="large-v3", choices=["tiny", "base", "small", "medium", "large-v3"], help="전사 모델(기본 large-v3)")
    run.add_argument("--language", default="ko", help="전사 언어 코드. 자동 감지는 --language auto")
    run.add_argument("--initial-prompt", default="", help="faster-whisper 용어 힌트(예: 초등 교육, 기초학력, 형성평가). 전사에만 적용")
    run.add_argument("--hotwords", default="", help="faster-whisper 용어 힌트(매 구간 적용, 긴 강의에 권장). 예: 교육연극, 행복교실, 형성평가")
    run.add_argument("--export-transcript", action="store_true", help="전사/자막을 transcript.txt와 transcript.srt로 별도 저장")
    run.add_argument("--source-url", help="선택: 타임스탬프 링크를 만들 YouTube URL")
    run.add_argument("--course", default="", help="과정명/강의명 메타데이터")
    run.add_argument("--lecturer", default="", help="강사 메타데이터")
    run.add_argument("--completed-on", default="", help="이수 일자(예: 2026-10-12)")
    run.add_argument("--pdf", type=Path, help="선택: 프로젝트에 함께 보관할 강의 PDF")
    run.add_argument("--reference", type=Path, action="append", default=[], help="참고 교안/자료 파일(여러 번 지정 가능, attachments/에 복사)")
    run.add_argument("--no-open", action="store_true", help="완료 후 HTML을 브라우저에서 열지 않음")

    download = subparsers.add_parser("download-authorized", help="사용 권한이 있는 공개 YouTube 영상을 다운로드합니다.")
    download.add_argument("url", help="YouTube 영상 URL")
    download.add_argument("--out", type=Path, required=True, help="저장 파일 경로")
    download.add_argument("--confirm-authorized", action="store_true", help="다운로드 권한 및 적용 약관을 확인했음을 명시")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "download-authorized":
            saved = download_authorized_video(args.url, args.out, args.confirm_authorized)
            print(f"다운로드 완료: {saved}")
            return 0

        video = args.video.expanduser().resolve()
        if not video.is_file():
            parser.error(f"영상 파일이 없습니다: {video}")
        if args.source_url and youtube_video_id(args.source_url) is None:
            parser.error("--source-url에는 지원하는 YouTube URL을 지정하세요.")
        crop = parse_crop(args.crop) if args.crop else select_crop(video)
        language = None if args.language.lower() == "auto" else args.language
        should_transcribe = (args.subtitle is None) if args.transcribe is None else args.transcribe
        output_dir = args.out if args.out else video.parent / f"{video.stem}_LectureCapture"
        report_path = run_pipeline(
            video_path=video,
            output_dir=output_dir,
            crop=crop,
            interval=args.interval,
            change_threshold=args.change_threshold,
            min_stable_seconds=args.min_stable,
            pixel_delta=args.pixel_delta,
            removal_threshold=args.removal_threshold,
            diagnose=args.diagnose,
            subtitle_path=args.subtitle,
            transcribe=should_transcribe,
            whisper_model=args.whisper_model,
            language=language,
            source_url=args.source_url,
            course=args.course,
            lecturer=args.lecturer,
            completed_on=args.completed_on,
            pdf_path=args.pdf,
            reference_paths=args.reference,
            export_transcript_files=args.export_transcript,
            initial_prompt=args.initial_prompt,
            hotwords=args.hotwords,
        )
        print(f"완료: {report_path}")
        print(f"Markdown 노트: {report_path.parent / 'note.md'}")
        print(f"프로젝트 데이터: {report_path.parent / 'project.json'}")
        if args.export_transcript:
            print(f"전사 TXT: {report_path.parent / 'transcript.txt'}")
            print(f"전사 SRT: {report_path.parent / 'transcript.srt'}")
        if not args.no_open:
            webbrowser.open(report_path.resolve().as_uri())
        return 0
    except KeyboardInterrupt:
        print("사용자가 실행을 중단했습니다.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
