"""일정DB: 구글 시트 한 탭. 열 이름(첫 행)으로 읽으니 열 순서는 바뀌어도 된다.

열: 키 | 날짜 | 구분 | 내용 | 상태 | 출처 | 대상   (대상 열은 없어도 동작)
"""
from __future__ import annotations

import csv
import json
import os

from .envload import resolve_path

REQUIRED = ["키", "날짜", "구분", "내용"]


def need(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise SystemExit(f"환경변수 {name}가 필요합니다 (.env 또는 GitHub Secrets).")
    return v


class MemoryDb:
    def __init__(self, rows: list[dict] | None = None):
        self._rows = [dict(r) for r in (rows or [])]

    def rows(self) -> list[dict]:
        return [dict(r) for r in self._rows]

    def append(self, rows: list[dict]) -> None:
        self._rows.extend(dict(r) for r in rows)

    def inbox(self):
        return None


class CsvDb(MemoryDb):
    """로컬 시험용 읽기 전용 DB."""

    def __init__(self, path: str):
        with open(path, encoding="utf-8-sig", newline="") as f:
            super().__init__(list(csv.DictReader(f)))

    def append(self, rows: list[dict]) -> None:
        raise RuntimeError("CSV DB는 읽기 전용입니다 (--dry-run과 함께 쓰세요).")


class SheetsDb:
    def __init__(self, worksheet, spreadsheet=None):
        self._ws = worksheet
        self._sh = spreadsheet

    def inbox(self):
        """'빠른입력' 탭이 있으면 그 탭을, 없으면 None (탭 이름은 INBOX_TAB로 바꿀 수 있다)."""
        if self._sh is None:
            return None
        import gspread

        from .inbox import InboxSheet

        try:
            return InboxSheet(self._sh.worksheet(os.environ.get("INBOX_TAB", "빠른입력")))
        except gspread.exceptions.WorksheetNotFound:
            return None

    def recipients(self):
        """'받는사람' 탭(친구에게 보내기 받는 사람)이 있으면 그 탭을, 없으면 None."""
        if self._sh is None:
            return None
        import gspread

        from .recipients import RecipientSheet

        try:
            return RecipientSheet(self._sh.worksheet("받는사람"))  # 챗봇(Apps Script)과 같은 이름으로 고정
        except gspread.exceptions.WorksheetNotFound:
            return None

    def share_tab(self):
        """'공유링크' 탭(없으면 만든다). 시트가 아니면 None."""
        if self._sh is None:
            return None
        import gspread

        from .recipients import ShareTab

        try:
            ws = self._sh.worksheet("공유링크")
        except gspread.exceptions.WorksheetNotFound:
            ws = self._sh.add_worksheet("공유링크", rows=10, cols=2)
        return ShareTab(ws)

    @classmethod
    def from_env(cls) -> "SheetsDb":
        import gspread  # 드라이런·테스트에는 필요 없으니 늦게 불러온다

        raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
        if raw:
            info = json.loads(raw)
        else:
            path = resolve_path(need("GOOGLE_SERVICE_ACCOUNT_FILE"))
            if not path.is_file():
                raise SystemExit(f"서비스 계정 키 파일을 찾을 수 없습니다: {path}")
            info = json.loads(path.read_text(encoding="utf-8"))
        gc = gspread.service_account_from_dict(info)
        email = info.get("client_email", "(키 파일에 client_email 없음)")  # 공유 대상 안내용: 비밀이 아님
        tab = os.environ.get("DB_TAB", "일정DB")
        try:
            sh = gc.open_by_key(need("DB_SHEET_ID"))
        except PermissionError:
            raise SystemExit(
                "일정DB 시트에 접근할 수 없습니다(403). 시트 '공유'에 아래 계정을 편집자로 추가했는지, "
                f"DB_SHEET_ID가 맞는지 확인하세요.\n  서비스 계정: {email}"
            ) from None
        except gspread.exceptions.SpreadsheetNotFound:
            raise SystemExit("DB_SHEET_ID에 해당하는 시트가 없습니다. 주소의 /d/ 뒤 ID인지 확인하세요.") from None
        try:
            return cls(sh.worksheet(tab), sh)
        except gspread.exceptions.WorksheetNotFound:
            raise SystemExit(f"일정DB 시트에 '{tab}' 탭이 없습니다. 탭 이름을 맞추거나 .env에 DB_TAB을 지정하세요.") from None

    def _header(self, vals: list[list[str]]) -> list[str]:
        header = [h.strip() for h in vals[0]] if vals else []
        missing = [h for h in REQUIRED if h not in header]
        if missing:
            raise ValueError(f"일정DB 첫 행에 열 이름이 없습니다: {', '.join(missing)}")
        return header

    def rows(self) -> list[dict]:
        vals = self._ws.get_all_values()
        if not vals:
            return []
        header = self._header(vals)
        out = []
        for row in vals[1:]:
            row = row + [""] * (len(header) - len(row))
            rec = dict(zip(header, row))
            if (rec.get("키") or rec.get("날짜") or rec.get("내용") or "").strip():
                out.append(rec)
        return out

    def append(self, rows: list[dict]) -> None:
        if not rows:
            return
        header = self._header(self._ws.get_all_values())
        values = [[r.get(h, "") for h in header] for r in rows]
        # RAW: 날짜를 시트가 멋대로 바꾸지 않게 문자열 그대로 넣는다
        self._ws.append_rows(values, value_input_option="RAW")
