"""
지도서 폴더(D:\지도서)를 기준으로 사용 가능한 과목을 자동 감지해
진도표 행을 생성하고, 필요하면 구글 시트 업로드까지 이어주는 원샷 스크립트.

기본 동작:
  python map_general_guides_to_sheet.py

옵션 예시:
  python map_general_guides_to_sheet.py --subject 사회
  python map_general_guides_to_sheet.py --subject 국어,도덕,수학 --upload
  python map_general_guides_to_sheet.py --all-presets --cleanup --upload
  python sheet_uploader/upload_generated_rows.py --cleanup
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from map_guides_to_sheet import (
    GUIDE_DIR,
    generate_general_data,
    generate_korean_data,
    generate_moral_data,
    iter_search_pdfs,
)
from sheet_uploader.core import (
    REPLACE_ALL,
    REPLACE_APPEND,
    REPLACE_SUBJECTS,
    upload_rows_to_sheet,
)


SCHEDULE_DIR = Path(__file__).resolve().parent
GENERATED_ROWS_DIR = SCHEDULE_DIR / "generated_rows"

GENERAL_SUBJECT_PRESETS = {
    "수학": {"kind": "general", "prefix": "수학", "max_unit": 6, "grade_str": "3-1", "disable_heuristic": False, "snapshot_name": "math"},
    "사회": {"kind": "general", "prefix": "사회", "max_unit": 4, "grade_str": "3-1", "disable_heuristic": True, "snapshot_name": "social"},
    "과학": {"kind": "general", "prefix": "과학", "max_unit": 5, "grade_str": "3-1", "disable_heuristic": False, "snapshot_name": "science"},
    "음악": {"kind": "general", "prefix": "음악", "max_unit": 8, "grade_str": "3", "disable_heuristic": False, "snapshot_name": "music"},
    "미술": {"kind": "general", "prefix": "미술", "max_unit": 8, "grade_str": "3", "disable_heuristic": False, "snapshot_name": "art"},
    "체육": {"kind": "general", "prefix": "체육", "max_unit": 5, "grade_str": "3", "disable_heuristic": False, "snapshot_name": "pe"},
    "영어": {"kind": "general", "prefix": "영어", "max_unit": 11, "grade_str": "3", "disable_heuristic": False, "snapshot_name": "english"},
    "실과": {"kind": "general", "prefix": "실과", "max_unit": 6, "grade_str": "5", "disable_heuristic": False, "snapshot_name": "practical"},
}

SPECIAL_SUBJECT_PRESETS = {
    "국어": {"kind": "special", "prefix": "국어", "grade_str": "3-1", "snapshot_name": "korean"},
    "도덕": {"kind": "special", "prefix": "도덕", "grade_str": "3", "snapshot_name": "moral"},
}

SUBJECT_ORDER = [
    "국어",
    "도덕",
    "수학",
    "사회",
    "과학",
    "음악",
    "미술",
    "체육",
    "영어",
    "실과",
]

SUBJECT_PRESETS = {
    **SPECIAL_SUBJECT_PRESETS,
    **GENERAL_SUBJECT_PRESETS,
}

YES_ANSWERS = {"", "y", "yes", "ㅇ", "예"}
NO_ANSWERS = {"n", "no", "ㄴ", "아니오"}


def split_subject_names(subject_text):
    return [part.strip() for part in str(subject_text).split(",") if part.strip()]


def build_subject_config(subject_name, *, prefix=None, grade_str=None, max_unit=None, disable_heuristic=None, kind=None):
    preset = dict(SUBJECT_PRESETS.get(subject_name, {}))

    return {
        "subject_name": subject_name,
        "kind": kind if kind is not None else preset.get("kind", "general"),
        "prefix": prefix if prefix is not None else preset.get("prefix", subject_name),
        "grade_str": grade_str if grade_str is not None else preset.get("grade_str", "3-1"),
        "max_unit": max_unit if max_unit is not None else preset.get("max_unit"),
        "disable_heuristic": (
            disable_heuristic
            if disable_heuristic is not None
            else preset.get("disable_heuristic", False)
        ),
        "snapshot_name": preset.get("snapshot_name", subject_name),
    }


def resolve_subject_configs(
    *,
    subject_name=None,
    use_all_presets=False,
    prefix=None,
    grade_str=None,
    max_unit=None,
    disable_heuristic=None,
):
    if use_all_presets:
        subject_names = [name for name in SUBJECT_ORDER if name in SUBJECT_PRESETS]
    elif subject_name:
        subject_names = split_subject_names(subject_name)
    else:
        raise ValueError("`--subject` 또는 `--all-presets` 중 하나는 필요합니다.")

    return [
        build_subject_config(
            name,
            prefix=prefix,
            grade_str=grade_str,
            max_unit=max_unit,
            disable_heuristic=disable_heuristic,
        )
        for name in subject_names
    ]


def subject_has_guide_material(config):
    guide_root = Path(GUIDE_DIR)
    if not guide_root.exists():
        return False
    return any(iter_search_pdfs(config["prefix"], [GUIDE_DIR]))


def detect_available_subject_configs():
    configs = []
    for subject_name in SUBJECT_ORDER:
        config = build_subject_config(subject_name)
        if subject_has_guide_material(config):
            configs.append(config)
    return configs


def generate_rows_for_config(config):
    subject_name = config["subject_name"]
    kind = config.get("kind", SUBJECT_PRESETS.get(subject_name, {}).get("kind", "general"))

    if kind == "special":
        if subject_name == "국어":
            return generate_korean_data()
        if subject_name == "도덕":
            return generate_moral_data()
        raise ValueError(f"unknown special subject: {subject_name}")

    return generate_general_data(
        subject_name,
        config["prefix"],
        max_unit=config["max_unit"] or 5,
        disable_heuristic=config["disable_heuristic"],
        grade_str=config["grade_str"],
    )


def generate_rows_for_configs(configs):
    rows = []
    summaries = []

    for config in configs:
        subject_rows = generate_rows_for_config(config)
        rows.extend(subject_rows)
        summaries.append((config, subject_rows))

    return rows, summaries


def print_preset_list():
    print("[기본 preset 목록]")
    for subject_name in SUBJECT_ORDER:
        if subject_name not in SUBJECT_PRESETS:
            continue
        config = SUBJECT_PRESETS[subject_name]
        print(
            f"  - {subject_name}: kind={config['kind']}, prefix={config['prefix']}, "
            f"grade={config.get('grade_str', '')}, max_unit={config.get('max_unit', '-')}, "
            f"disable_heuristic={config.get('disable_heuristic', False)}"
        )


def choose_configs_interactively(input_fn=input):
    print_preset_list()
    print("\n[안내] 생성할 과목을 입력하세요.")
    print("  - 예: 사회, 과학, 미술")
    print("  - all: 모든 preset")
    print("  - auto: D:\\지도서 자동 감지")
    print("  - Enter: 종료")

    while True:
        choice = input_fn("과목명 입력: ").strip()
        if not choice:
            return []
        if choice.lower() == "all":
            return resolve_subject_configs(use_all_presets=True)
        if choice.lower() == "auto":
            return detect_available_subject_configs()
        return resolve_subject_configs(subject_name=choice)


def preview_generated_rows(summaries):
    for config, rows in summaries:
        print(
            f"\n[{config['subject_name']}] {len(rows)}행 생성됨 "
            f"(kind={config['kind']}, prefix={config['prefix']}, "
            f"grade={config['grade_str']}, max_unit={config.get('max_unit', '-')}, "
            f"disable_heuristic={config.get('disable_heuristic', False)})"
        )
        for row in rows[:5]:
            print(
                f"    {row['과목']} | {row.get('대단원', '')[:25]:<25} | "
                f"{row.get('차시', ''):<8} | {row.get('수업내용', '')[:40]}"
            )
        if len(rows) > 5:
            print(f"    ... 외 {len(rows) - 5}행")


def confirm_upload_action(input_fn=input, print_fn=print):
    print_fn("\n[확인] Enter를 누르면 바로 업로드합니다. 미리보기만 하고 끝내려면 n 을 입력하세요.")

    while True:
        choice = input_fn("업로드할까요? [Y/n]: ").strip().lower()
        if choice in YES_ANSWERS:
            break
        if choice in NO_ANSWERS:
            return False, False, REPLACE_APPEND
        print_fn("  Enter, y, n 중 하나로 입력해 주세요.")

    print_fn("\n  업로드 방식을 선택하세요.")
    print_fn("    1. 그대로 추가")
    print_fn("    2. 이번에 생성한 과목 기존 행을 지우고 업로드 (Enter=2, Recommended)")
    print_fn("    3. 진도표 전체 기존 행을 지우고 업로드")

    while True:
        choice = input_fn("  선택: ").strip().lower()
        if choice in {"", "2"}:
            return True, False, REPLACE_SUBJECTS
        if choice in {"3", "all", "replace-all"}:
            return True, False, REPLACE_ALL
        if choice in {"1", "append"}:
            break
        print_fn("  1, 2, 3 중 하나로 입력해 주세요.")

    while True:
        choice = input_fn("업로드 전에 중복 행을 삭제할까요? [y/N]: ").strip().lower()
        if choice in {"", *NO_ANSWERS}:
            return True, False, REPLACE_APPEND
        if choice in YES_ANSWERS - {""}:
            return True, True, REPLACE_APPEND
        print_fn("  Enter, y, n 중 하나로 입력해 주세요.")


def resolve_replace_mode(args):
    if getattr(args, "replace_all", False):
        return REPLACE_ALL
    if getattr(args, "replace_subjects", False):
        return REPLACE_SUBJECTS
    return REPLACE_APPEND


def write_generation_artifacts(summaries, rows):
    GENERATED_ROWS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generated_at = datetime.now().isoformat(timespec="seconds")
    run_dir = GENERATED_ROWS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    summary_payload = {
        "generated_at": generated_at,
        "guide_dir": GUIDE_DIR,
        "subject_count": len(summaries),
        "total_row_count": len(rows),
        "subjects": [
            {
                "subject_name": config["subject_name"],
                "kind": config["kind"],
                "prefix": config["prefix"],
                "grade_str": config["grade_str"],
                "row_count": len(subject_rows),
                "snapshot_name": config["snapshot_name"],
            }
            for config, subject_rows in summaries
        ],
    }
    all_rows_payload = {
        **summary_payload,
        "rows": rows,
    }

    (run_dir / "summary.json").write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "all_rows.json").write_text(
        json.dumps(all_rows_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (GENERATED_ROWS_DIR / "latest_summary.json").write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (GENERATED_ROWS_DIR / "latest_all_rows.json").write_text(
        json.dumps(all_rows_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for config, subject_rows in summaries:
        payload = {
            "generated_at": generated_at,
            "subject_name": config["subject_name"],
            "kind": config["kind"],
            "prefix": config["prefix"],
            "grade_str": config["grade_str"],
            "row_count": len(subject_rows),
            "rows": subject_rows,
        }
        filename = f"{config['snapshot_name']}.json"
        latest_filename = f"latest_{config['snapshot_name']}.json"
        (run_dir / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (GENERATED_ROWS_DIR / latest_filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return run_dir


def print_detected_configs(configs):
    if not configs:
        print("[자동 감지] D:\\지도서에서 사용할 수 있는 지도서를 찾지 못했습니다.")
        return

    print("[자동 감지]")
    for config in configs:
        print(
            f"  - {config['subject_name']} "
            f"(kind={config['kind']}, prefix={config['prefix']}, grade={config['grade_str']})"
        )


def main():
    parser = argparse.ArgumentParser(description="지도서 폴더 자동 감지 기반 진도표 생성/업로드 스크립트")
    parser.add_argument("--subject", help="생성할 과목명. 쉼표로 여러 과목 지정 가능 (예: 국어,도덕,사회)")
    parser.add_argument("--all-presets", action="store_true", help="알고 있는 모든 preset 과목을 생성")
    parser.add_argument("--auto-detect", action="store_true", help="D:\\지도서에서 가능한 과목을 자동 감지")
    parser.add_argument("--interactive", action="store_true", help="대화형 과목 선택 모드")
    parser.add_argument("--list-presets", action="store_true", help="기본 preset 목록 보기")
    parser.add_argument("--prefix", help="PDF 검색용 과목 키워드 override")
    parser.add_argument("--grade", dest="grade_str", help="학년/학기 문자열 override (예: 3-1, 3)")
    parser.add_argument("--max-unit", type=int, help="최대 단원 수 override")
    parser.add_argument("--disable-heuristic", action="store_true", help="일반 과목 heuristic 제목 추출 끄기")
    parser.add_argument("--upload", action="store_true", help="실제 구글 시트에 업로드")
    parser.add_argument("--cleanup", action="store_true", help="업로드 전 중복 행 삭제")
    parser.add_argument("--replace-subjects", action="store_true", help="업로드할 과목의 기존 행을 지우고 업로드")
    parser.add_argument("--replace-all", action="store_true", help="진도표의 기존 행 전체를 지우고 업로드")
    args = parser.parse_args()

    if args.replace_subjects and args.replace_all:
        parser.error("--replace-subjects와 --replace-all은 같이 사용할 수 없습니다.")

    print("=" * 60)
    print("  📚 지도서 폴더 자동 감지 → 진도표 생성 스크립트")
    print("=" * 60)

    if args.list_presets:
        print_preset_list()
        return

    if args.subject or args.all_presets:
        configs = resolve_subject_configs(
            subject_name=args.subject,
            use_all_presets=args.all_presets,
            prefix=args.prefix,
            grade_str=args.grade_str,
            max_unit=args.max_unit,
            disable_heuristic=True if args.disable_heuristic else None,
        )
    elif args.interactive:
        configs = choose_configs_interactively()
    else:
        configs = detect_available_subject_configs()
        print_detected_configs(configs)

    if not configs:
        print("\n[종료] 생성할 과목이 없습니다.")
        return

    rows, summaries = generate_rows_for_configs(configs)
    preview_generated_rows(summaries)
    artifact_dir = write_generation_artifacts(summaries, rows)

    print(f"\n[저장] 생성 결과 보관 폴더: {artifact_dir}")
    print(f"[저장] 최신 전체 rows: {GENERATED_ROWS_DIR / 'latest_all_rows.json'}")
    print(f"[저장] 업로드 전용 스크립트: {SCHEDULE_DIR / 'sheet_uploader' / 'upload_generated_rows.py'}")

    if not args.upload and not args.cleanup:
        if rows and sys.stdin.isatty():
            try:
                upload_now, cleanup_now, replace_mode = confirm_upload_action()
            except EOFError:
                upload_now, cleanup_now, replace_mode = (False, False, REPLACE_APPEND)
            if upload_now:
                upload_rows_to_sheet(rows, cleanup=cleanup_now, replace_mode=replace_mode)
                return

        print(f"\n[미리보기 모드] 총 {len(rows)}행.")
        print("  실제 업로드:      python map_general_guides_to_sheet.py --upload")
        print("  과목만 교체 업로드: python map_general_guides_to_sheet.py --upload --replace-subjects")
        print("  전체 교체 업로드:   python map_general_guides_to_sheet.py --upload --replace-all")
        print("  중복삭제+업로드:  python map_general_guides_to_sheet.py --upload --cleanup")
        print("  저장본 업로드:    python sheet_uploader/upload_generated_rows.py --replace-subjects")
        return

    upload_rows_to_sheet(rows, cleanup=args.cleanup, replace_mode=resolve_replace_mode(args))


if __name__ == "__main__":
    main()
