"""
기타 교과용 범용 지도서 PDF → 구글 시트 진도표 매핑 스크립트.

국어/도덕 전용 매핑은 `map_guides_to_sheet.py`를 사용한다.

사용법:
  python map_general_guides_to_sheet.py --list-presets
  python map_general_guides_to_sheet.py --subject 사회
  python map_general_guides_to_sheet.py --subject 과학 --upload
  python map_general_guides_to_sheet.py --all-presets --upload --cleanup
"""

import argparse
import sys

from map_guides_to_sheet import (
    build_row_for_headers,
    delete_duplicate_rows,
    generate_general_data,
    get_sheet,
)


SUBJECT_PRESETS = {
    "수학": {"prefix": "수학", "max_unit": 6, "grade_str": "3-1", "disable_heuristic": False},
    "사회": {"prefix": "사회", "max_unit": 4, "grade_str": "3-1", "disable_heuristic": True},
    "과학": {"prefix": "과학", "max_unit": 5, "grade_str": "3-1", "disable_heuristic": False},
    "음악": {"prefix": "음악", "max_unit": 8, "grade_str": "3", "disable_heuristic": False},
    "미술": {"prefix": "미술", "max_unit": 8, "grade_str": "3", "disable_heuristic": False},
    "체육": {"prefix": "체육", "max_unit": 5, "grade_str": "3", "disable_heuristic": False},
    "영어": {"prefix": "영어", "max_unit": 11, "grade_str": "3", "disable_heuristic": False},
    "실과": {"prefix": "실과", "max_unit": 6, "grade_str": "5", "disable_heuristic": False},
}

YES_ANSWERS = {"", "y", "yes", "ㅇ", "예", "네"}
NO_ANSWERS = {"n", "no", "ㄴ", "아니오", "아니요"}


def build_subject_config(subject_name, *, prefix=None, grade_str=None, max_unit=None, disable_heuristic=None):
    preset = dict(SUBJECT_PRESETS.get(subject_name, {}))

    return {
        "subject_name": subject_name,
        "prefix": prefix if prefix is not None else preset.get("prefix", subject_name),
        "grade_str": grade_str if grade_str is not None else preset.get("grade_str", "3-1"),
        "max_unit": max_unit if max_unit is not None else preset.get("max_unit", 5),
        "disable_heuristic": (
            disable_heuristic
            if disable_heuristic is not None
            else preset.get("disable_heuristic", False)
        ),
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
        subject_names = list(SUBJECT_PRESETS.keys())
    elif subject_name:
        subject_names = [subject_name]
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


def generate_rows_for_configs(configs):
    rows = []
    summaries = []

    for config in configs:
        subject_rows = generate_general_data(
            config["subject_name"],
            config["prefix"],
            max_unit=config["max_unit"],
            disable_heuristic=config["disable_heuristic"],
            grade_str=config["grade_str"],
        )
        rows.extend(subject_rows)
        summaries.append((config, subject_rows))

    return rows, summaries


def print_preset_list():
    print("[기본 preset 목록]")
    for subject_name, config in SUBJECT_PRESETS.items():
        print(
            f"  - {subject_name}: prefix={config['prefix']}, "
            f"grade={config['grade_str']}, max_unit={config['max_unit']}, "
            f"disable_heuristic={config['disable_heuristic']}"
        )


def choose_configs_interactively(input_fn=input):
    print_preset_list()
    print("\n[안내] 생성할 과목을 입력하세요.")
    print("  - 예: 사회, 과학, 미술")
    print("  - all: preset 전체")
    print("  - Enter: 종료")

    while True:
        choice = input_fn("과목명 입력: ").strip()
        if not choice:
            return []
        if choice.lower() == "all":
            return resolve_subject_configs(use_all_presets=True)
        return resolve_subject_configs(subject_name=choice)


def preview_generated_rows(summaries):
    for config, rows in summaries:
        print(
            f"\n[{config['subject_name']}] {len(rows)}행 생성됨 "
            f"(prefix={config['prefix']}, grade={config['grade_str']}, "
            f"max_unit={config['max_unit']}, disable_heuristic={config['disable_heuristic']})"
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
            return False, False
        print_fn("  Enter, y, n 중 하나로 입력해 주세요.")

    while True:
        choice = input_fn("업로드 전에 중복 행을 삭제할까요? [y/N]: ").strip().lower()
        if choice in {"", *NO_ANSWERS}:
            return True, False
        if choice in YES_ANSWERS - {""}:
            return True, True
        print_fn("  Enter, y, n 중 하나로 입력해 주세요.")


def upload_rows(rows, *, cleanup=False):
    sh, ws = get_sheet()
    headers = ws.row_values(1)
    print(f"\n[업로드] 헤더: {headers}")

    if cleanup:
        print("\n  [중복 삭제 중...]")
        deleted = delete_duplicate_rows(ws)
        print(f"  {deleted}개 중복 행 삭제됨")

    new_rows = [build_row_for_headers(headers, row) for row in rows]
    if new_rows:
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")
        print(f"\n  ✅ {len(new_rows)}행 업로드 완료!")
    else:
        print("\n  [알림] 업로드할 행이 없습니다.")


def main():
    parser = argparse.ArgumentParser(description="기타 교과용 범용 지도서 PDF → 진도표 구글시트 매핑")
    parser.add_argument("--subject", help="생성할 과목명 (예: 사회, 과학, 미술)")
    parser.add_argument("--all-presets", action="store_true", help="기본 preset 과목 전체를 생성")
    parser.add_argument("--list-presets", action="store_true", help="기본 preset 목록 보기")
    parser.add_argument("--prefix", help="PDF 탐색용 과목 키워드 override")
    parser.add_argument("--grade", dest="grade_str", help="학년/학기 문자열 (예: 3-1, 3)")
    parser.add_argument("--max-unit", type=int, help="최대 단원 수 override")
    parser.add_argument(
        "--disable-heuristic",
        action="store_true",
        help="연간 지도 계획 또는 휴리스틱 차시 파싱 없이 단원/차시 기본값으로 생성",
    )
    parser.add_argument("--upload", action="store_true", help="실제 구글 시트에 업로드")
    parser.add_argument("--cleanup", action="store_true", help="중복 행 삭제 포함")
    args = parser.parse_args()

    print("=" * 60)
    print("  📚 기타 교과용 범용 지도서 → 진도표 매핑 스크립트")
    print("=" * 60)

    if args.list_presets:
        print_preset_list()
        return

    if not args.subject and not args.all_presets:
        configs = choose_configs_interactively()
        if not configs:
            print("\n[종료] 과목 선택 없이 프로그램을 마칩니다.")
            return
    else:
        configs = resolve_subject_configs(
            subject_name=args.subject,
            use_all_presets=args.all_presets,
            prefix=args.prefix,
            grade_str=args.grade_str,
            max_unit=args.max_unit,
            disable_heuristic=True if args.disable_heuristic else None,
        )

    rows, summaries = generate_rows_for_configs(configs)
    preview_generated_rows(summaries)

    if not args.upload and not args.cleanup:
        if rows and sys.stdin.isatty():
            upload_now, cleanup_now = confirm_upload_action()
            if upload_now:
                upload_rows(rows, cleanup=cleanup_now)
                return
        print(f"\n[미리보기 모드] 총 {len(rows)}행.")
        print("  실제 업로드:      python map_general_guides_to_sheet.py --subject 사회 --upload")
        print("  중복삭제+업로드:  python map_general_guides_to_sheet.py --subject 사회 --upload --cleanup")
        return

    upload_rows(rows, cleanup=args.cleanup)


if __name__ == "__main__":
    main()
