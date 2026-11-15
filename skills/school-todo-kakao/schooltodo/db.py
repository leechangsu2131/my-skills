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


class CsvDb(MemoryDb):
    """로컬 시험용 읽기 전용 DB."""

    def __init__(self, path: str):
        with open(path, encoding="utf-8-sig", newline="") as f:
            super().__init__(list(csv.DictReader(f)))

    def append(self, rows: list[dict]) -> None:
        raise RuntimeError("CSV DB는 읽기 전용입니다 (--dry-run과 함께 쓰세요).")


class SheetsDb:
    def __init__(self, worksheet):
        self._ws = worksheet

    @classmethod
    def from_env(cls) -> "SheetsDb":
        import gspread  # 드라이런·테스트에는 필요 없으니 늦게 불러온다

        raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
        if raw:
            gc = gspread.service_account_from_dict(json.loads(raw))
        else:
            path = resolve_path(need("GOOGLE_SERVICE_ACCOUNT_FILE"))
            if not path.is_file():
                raise SystemExit(f"서비스 계정 키 파일을 찾을 수 없습니다: {path}")
            gc = gspread.service_account(filename=str(path))
        tab = os.environ.get("DB_TAB", "일정DB")
        return cls(gc.open_by_key(need("DB_SHEET_ID")).worksheet(tab))

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
