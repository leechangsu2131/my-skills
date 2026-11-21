"""구글시트 "투자시트 업그레이드" 읽기·쓰기 도우미 (Claude·사람 공용).

설정: 공용 .env (OneDrive "96. 인증/.env", my-skills 공용 파일)에서 읽는다. 코드에 시트 ID를 두지 않는다.
      PERSONAL_INVEST_SHEET__GOOGLE_SHEET_ID   시트 ID (필수)
      GOOGLE_CREDENTIALS_PATH                  서비스 계정 키 경로 (없으면 같은 폴더의 credentials.json)
      .env 는 my-skills skills/_shared/skill_env.py 가 찾는다. 같은 이름의 OS 환경변수가 있으면 그것이 우선.
인증: 서비스 계정(시트에 편집자로 공유됨)
실행: gspread가 설치된 파이썬.  Windows 콘솔 한글/이모지 때문에 -X utf8 로 실행.

  py -X utf8 sheet_io.py tabs
  py -X utf8 sheet_io.py read  "📒 매매일지!A1:H10"            # 화면에 보이는 값
  py -X utf8 sheet_io.py read  "📒 매매일지!A1:H10" --formula  # 수식 그대로
  py -X utf8 sheet_io.py write "📒 매매일지!A962:H963" rows.tsv  # 미리보기만 (쓰지 않음)
  py -X utf8 sheet_io.py write "📒 매매일지!A962:H963" rows.tsv --apply

쓰기 규칙 (00_총괄_투자시스템 §9):
  - 한 번에 5행 이내
  - 대상 범위가 비어 있지 않으면 거부 (--overwrite 를 줘야 덮어씀; 기존 값을 먼저 보여 줌)
  - 기본은 미리보기, --apply 일 때만 씀
  - 쓴 뒤 다시 읽어 입력값과 비교
  - 열 삽입·삭제 같은 구조 변경 기능은 일부러 넣지 않음
"""
import argparse
import csv
import io
import os
import pathlib
import sys

import gspread

sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents
                            if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import central_env_path, env_values  # noqa: E402

MAX_ROWS = 5
SKILL = "personal-invest-sheet"


def config():
    env_path = central_env_path()
    vals = env_values(SKILL)  # PERSONAL_INVEST_SHEET__X 는 X 로 보인다
    get = lambda k: os.environ.get(k) or vals.get(k, "")
    sheet_id = get("GOOGLE_SHEET_ID")
    if not sheet_id:
        sys.exit(f"시트 ID가 없습니다. 공용 .env({env_path or '못 찾음'})에 PERSONAL_INVEST_SHEET__GOOGLE_SHEET_ID=... 를 넣어 주세요.")
    cred = os.path.expandvars(os.path.expanduser(get("GOOGLE_CREDENTIALS_PATH") or "credentials.json"))
    if not os.path.isabs(cred) and env_path:  # 상대 경로는 .env 가 있는 폴더 기준
        cred = os.path.join(os.path.dirname(os.path.expandvars(env_path)), cred)
    if not os.path.isfile(cred):
        sys.exit("서비스 계정 키 파일을 못 찾았습니다. 공용 .env의 GOOGLE_CREDENTIALS_PATH를 확인해 주세요.")
    return sheet_id, cred


def open_sheet():
    sheet_id, cred = config()
    return gspread.service_account(filename=cred).open_by_key(sheet_id)


def split_range(a1):
    if "!" not in a1:
        sys.exit("범위는 '탭이름!A1:B2' 형식이어야 합니다.")
    tab, rng = a1.rsplit("!", 1)
    return tab.strip("'"), rng


def show(rows):
    out = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
    for r in rows:
        out.writerow(r)


def read_tsv(path):
    text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8-sig").read()
    return [r for r in csv.reader(io.StringIO(text), delimiter="\t")]


def cmd_tabs(sh, _):
    for ws in sh.worksheets():
        print(f"{ws.title}\t{ws.row_count}x{ws.col_count}")


def cmd_read(sh, a):
    tab, rng = split_range(a.range)
    opt = "FORMULA" if a.formula else ("UNFORMATTED_VALUE" if a.raw else "FORMATTED_VALUE")
    show(sh.worksheet(tab).get(rng, value_render_option=opt))


def cmd_write(sh, a):
    tab, rng = split_range(a.range)
    rows = read_tsv(a.tsv)
    if not rows:
        sys.exit("입력 행이 없습니다.")
    if len(rows) > MAX_ROWS:
        sys.exit(f"거부: {len(rows)}행. 한 번에 {MAX_ROWS}행 이내로 나눠 주세요.")
    ws = sh.worksheet(tab)
    gr = gspread.utils.a1_range_to_grid_range(rng)
    n_rows = gr["endRowIndex"] - gr["startRowIndex"]
    n_cols = gr["endColumnIndex"] - gr["startColumnIndex"]
    width = max(len(r) for r in rows)
    if len(rows) != n_rows or width > n_cols:
        sys.exit(f"거부: 범위 {rng}는 {n_rows}행x{n_cols}열인데 입력은 {len(rows)}행x{width}열.")

    existing = ws.get(rng, value_render_option="FORMULA")
    filled = [(i, j, v) for i, r in enumerate(existing) for j, v in enumerate(r) if str(v).strip() != ""]
    print(f"[대상] {tab}!{rng}")
    if filled:
        print(f"[기존 값 {len(filled)}칸 있음]")
        show(existing)
        if not a.overwrite:
            sys.exit("거부: 대상 범위가 비어 있지 않습니다. 덮어쓰려면 --overwrite.")
    print("[쓸 값]")
    show(rows)
    if not a.apply:
        print("(미리보기. 실제로 쓰려면 --apply)")
        return

    ws.update(rows, rng, value_input_option="USER_ENTERED")
    after = ws.get(rng, value_render_option="FORMULA")
    bad = []
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            got = after[i][j] if i < len(after) and j < len(after[i]) else ""
            if str(got) != v and not _num_eq(got, v):
                bad.append((i, j, v, got))
    if bad:
        print(f"[확인 실패 {len(bad)}칸] (행,열,입력,시트값)")
        for b in bad:
            print("  ", b)
        sys.exit(1)
    print("[쓰기 완료, 다시 읽어 일치 확인]")


def _num_eq(got, v):
    try:
        return float(got) == float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return False


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tabs")
    r = sub.add_parser("read")
    r.add_argument("range")
    r.add_argument("--formula", action="store_true", help="수식 그대로")
    r.add_argument("--raw", action="store_true", help="서식 없는 원값")
    w = sub.add_parser("write")
    w.add_argument("range")
    w.add_argument("tsv", help="TSV 파일 경로, '-'면 표준입력")
    w.add_argument("--apply", action="store_true")
    w.add_argument("--overwrite", action="store_true")
    a = p.parse_args()
    sh = open_sheet()
    {"tabs": cmd_tabs, "read": cmd_read, "write": cmd_write}[a.cmd](sh, a)


if __name__ == "__main__":
    main()
