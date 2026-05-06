"""
gsheet_auth.py
──────────────
Google Sheets 인증 헬퍼 — .env 기반 (service_account.json 불필요)

인증 우선순위:
  1. .env 파일의 GOOGLE_SA_* 환경변수
  2. (폴백) service_account.json 파일 (하위호환)
  3. (폴백) gspread OAuth (브라우저 인증)
"""

import os
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

BASE_DIR = Path(__file__).parent.resolve()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _load_dotenv() -> None:
    """Load .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        env_path = BASE_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
    except ImportError:
        pass  # python-dotenv not installed — rely on system env vars


def _build_sa_info_from_env() -> dict | None:
    """Build service account info dict from GOOGLE_SA_* env vars."""
    project_id = os.environ.get("GOOGLE_SA_PROJECT_ID")
    private_key = os.environ.get("GOOGLE_SA_PRIVATE_KEY")
    client_email = os.environ.get("GOOGLE_SA_CLIENT_EMAIL")

    if not all([project_id, private_key, client_email]):
        return None

    # dotenv sometimes keeps surrounding quotes — strip them
    if private_key.startswith('"') and private_key.endswith('"'):
        private_key = private_key[1:-1]
    # Restore actual newlines (env files store \\n as literal backslash-n)
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


def get_client() -> gspread.Client:
    """
    Google Sheets 클라이언트를 반환합니다.

    인증 우선순위:
      1. .env → GOOGLE_SA_* 환경변수로 인증
      2. service_account.json 파일 (하위호환)
      3. gspread OAuth 브라우저 인증
    """
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


def get_sheet_id() -> str:
    """
    스프레드시트 ID를 반환합니다.

    우선순위:
      1. .env → GOOGLE_SHEET_ID 환경변수
      2. sheet_id.txt 파일 (하위호환)
    """
    _load_dotenv()

    # 1) .env 환경변수
    env_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if env_id:
        return env_id

    # 2) sheet_id.txt 파일 (하위호환)
    id_file = BASE_DIR / "sheet_id.txt"
    if id_file.exists():
        return id_file.read_text().strip()

    raise FileNotFoundError(
        "GOOGLE_SHEET_ID(.env)도 sheet_id.txt도 없습니다.\n"
        ".env에 GOOGLE_SHEET_ID를 설정하거나 1_setup_gsheet.py를 먼저 실행하세요."
    )
