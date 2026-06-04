"""
gsheet.py
─────────
구글시트 연동 — 기존 personal-record-trade/gsheet_auth.py 패턴을 벤치마킹.

시트 구조:
  Sheet1 "키워드"     — 검색 키워드 목록 (읽기)
  Sheet2 "수집데이터"  — 매물 데이터 append (쓰기)
  Sheet3 "대시보드"    — 통계 요약 (쓰기)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from collector.models import Product

BASE_DIR = Path(__file__).parent.parent.resolve()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# ──────────────────────────────────────────────
# 인증 (gsheet_auth.py 벤치마킹)
# ──────────────────────────────────────────────

def _load_dotenv() -> None:
    """Load .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        env_path = BASE_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
    except ImportError:
        pass


def _build_sa_info_from_env() -> dict | None:
    """Build service account info dict from GOOGLE_SA_* env vars."""
    project_id = os.environ.get("GOOGLE_SA_PROJECT_ID")
    private_key = os.environ.get("GOOGLE_SA_PRIVATE_KEY")
    client_email = os.environ.get("GOOGLE_SA_CLIENT_EMAIL")

    if not all([project_id, private_key, client_email]):
        return None

    if private_key.startswith('"') and private_key.endswith('"'):
        private_key = private_key[1:-1]
    private_key = private_key.replace("\\n", "\n")

    return {
        "type": os.environ.get("GOOGLE_SA_TYPE", "service_account"),
        "project_id": project_id,
        "private_key_id": os.environ.get("GOOGLE_SA_PRIVATE_KEY_ID", ""),
        "private_key": private_key,
        "client_email": client_email,
        "client_id": os.environ.get("GOOGLE_SA_CLIENT_ID", ""),
        "auth_uri": os.environ.get("GOOGLE_SA_AUTH_URI",
                                   "https://accounts.google.com/o/oauth2/auth"),
        "token_uri": os.environ.get("GOOGLE_SA_TOKEN_URI",
                                    "https://oauth2.googleapis.com/token"),
        "auth_provider_x509_cert_url": os.environ.get(
            "GOOGLE_SA_AUTH_PROVIDER_CERT_URL",
            "https://www.googleapis.com/oauth2/v1/certs"),
        "client_x509_cert_url": os.environ.get("GOOGLE_SA_CLIENT_CERT_URL", ""),
        "universe_domain": "googleapis.com",
    }


def _get_client() -> gspread.Client:
    """Google Sheets 클라이언트를 반환한다."""
    _load_dotenv()

    # 1) .env 환경변수
    sa_info = _build_sa_info_from_env()
    if sa_info:
        creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
        return gspread.authorize(creds)

    # 2) service_account.json (하위호환)
    sa_json = BASE_DIR / "service_account.json"
    if sa_json.exists():
        creds = Credentials.from_service_account_file(str(sa_json), scopes=SCOPES)
        return gspread.authorize(creds)

    # 3) OAuth fallback
    return gspread.oauth()


def _get_sheet_id() -> str:
    """스프레드시트 ID를 반환한다."""
    _load_dotenv()
    env_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if env_id:
        return env_id
    raise ValueError(
        "GOOGLE_SHEET_ID가 .env에 설정되지 않았습니다.\n"
        ".env 파일에 GOOGLE_SHEET_ID=... 를 추가해주세요."
    )


# ──────────────────────────────────────────────
# 시트 관리 클래스
# ──────────────────────────────────────────────

class GSheetClient:
    """구글시트 읽기/쓰기 클라이언트."""

    SHEET_KEYWORDS = "키워드"
    SHEET_DATA = "수집데이터"
    SHEET_DASHBOARD = "대시보드"

    def __init__(self):
        self.client: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None

    def connect(self) -> None:
        """구글시트에 연결한다."""
        print("[GSheet] 구글시트 연결 중...")
        try:
            self.client = _get_client()
            sheet_id = _get_sheet_id()
            self.spreadsheet = self.client.open_by_key(sheet_id)
            print(f"[GSheet] ✅ 연결 성공: {self.spreadsheet.title}")
        except Exception as e:
            print(f"[GSheet] ❌ 연결 실패: {e}")
            raise

    def _get_or_create_worksheet(
        self, title: str, headers: list[str] | None = None
    ) -> gspread.Worksheet:
        """워크시트를 가져오거나 새로 만든다."""
        try:
            ws = self.spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = self.spreadsheet.add_worksheet(
                title=title, rows=1000, cols=20
            )
            if headers:
                ws.append_row(headers)
            print(f"[GSheet] 새 시트 생성: {title}")
        return ws

    def read_keywords(self) -> list[str]:
        """키워드 시트에서 키워드 목록을 읽는다."""
        try:
            ws = self.spreadsheet.worksheet(self.SHEET_KEYWORDS)
            values = ws.col_values(1)
            # 첫 행(헤더) 제외
            keywords = [v.strip() for v in values[1:] if v.strip()]
            print(f"[GSheet] 키워드 {len(keywords)}개 로드: {keywords}")
            return keywords
        except gspread.WorksheetNotFound:
            print("[GSheet] ℹ️ 키워드 시트 없음 — config.json 사용")
            return []

    def upload_products(self, products: list[Product]) -> int:
        """상품 데이터를 수집데이터 시트에 추가한다."""
        if not products:
            return 0

        ws = self._get_or_create_worksheet(
            self.SHEET_DATA,
            headers=Product.sheet_header(),
        )

        rows = [p.to_sheet_row() for p in products]

        # 일괄 추가 (batch)
        ws.append_rows(rows, value_input_option="USER_ENTERED")

        print(f"[GSheet] ✅ {len(rows)}건 업로드 완료")
        return len(rows)

    def update_dashboard(self, stats: dict) -> None:
        """대시보드 시트를 업데이트한다."""
        ws = self._get_or_create_worksheet(
            self.SHEET_DASHBOARD,
            headers=["키워드", "총 매물수", "마지막 수집"],
        )

        # 기존 데이터 클리어 (헤더 제외)
        try:
            ws.batch_clear(["A2:Z1000"])
        except Exception:
            pass

        by_keyword = stats.get("by_keyword", {})
        last = stats.get("last_collected", "")
        rows = [
            [kw, count, last]
            for kw, count in by_keyword.items()
        ]
        rows.append(["합계", stats.get("total", 0), last])

        if rows:
            ws.append_rows(rows, value_input_option="USER_ENTERED")

        print("[GSheet] ✅ 대시보드 업데이트 완료")
