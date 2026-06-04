"""
layer1_store.py - Layer 1 Raw Data Store (열 기반)
구글 시트 'raw data' 탭에 소스별 x 종목별 데이터를 열 헤더 기반으로 저장.
각 행 = (ticker, source) 조합, 각 열 = 지표(metric)

원칙:
  - 같은 개념 = 같은 열 (source 열이 출처를 구분)
  - Forward PE만 해석 차이로 열 분리 (NTM vs FY)
"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSONL_PATH = ROOT / "data" / "estimates_raw.jsonl"
RAW_DATA_GID = 1309880603

# 헤더 정의
HEADERS = [
    "ticker", "source", "as_of",
    # Valuation - 통합 열
    "pe_ratio", "ps_ratio", "pb_ratio", "ev_ebitda",
    # Forward PE - 해석 차이로 분리
    "fwd_pe_ntm",       # Yahoo: Next Twelve Months 기준
    "fwd_pe_fy",        # FinanceCharts: Fiscal Year 기준
    # PE 히스토리
    "pe_avg_3y", "pe_vs_3y",
    # 가치평가 - 통합 열
    "fair_value", "mos",
    # 퀄리티 지표
    "fin_strength", "profit_rank", "piotroski", "altman_z",
    "roic", "fcf_margin", "op_margin", "ev_fcf", "roiic_3y",
    "rev_cagr_1y", "rev_cagr_2y", "rev_cagr_3y",
    "52w_low",
]


def _ensure_jsonl():
    JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not JSONL_PATH.exists():
        JSONL_PATH.touch()


def save_row(ticker: str, source: str, data: dict):
    """
    소스 하나에서 수집한 지표 묶음을 한 행으로 저장.
    data = {"pe_ratio": 32.33, "fwd_pe_ntm": 16.68, ...}
    """
    as_of = datetime.today().strftime("%Y-%m-%d")
    record = {"ticker": ticker, "source": source, "as_of": as_of}
    record.update(data)

    # 1) 로컬 JSONL 백업
    _ensure_jsonl()
    with open(JSONL_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 2) 구글 시트 raw data 탭
    try:
        _upsert_to_sheet(ticker, source, as_of, data)
    except Exception as e:
        print(f"  [raw data 탭 저장 실패] {e}")


def _upsert_to_sheet(ticker: str, source: str, as_of: str, data: dict):
    """구글 시트에 행 upsert (같은 ticker+source 있으면 업데이트, 없으면 추가)"""
    import sys
    sys.path.insert(0, str(ROOT))
    from gsheet_auth import get_client, get_sheet_id

    client = get_client()
    doc = client.open_by_key(get_sheet_id())
    ws = doc.get_worksheet_by_id(RAW_DATA_GID)

    # 헤더 확인/설정
    existing_header = ws.row_values(1)
    if not existing_header or existing_header[0] != "ticker":
        ws.update(range_name="A1", values=[HEADERS], value_input_option="USER_ENTERED")

    # 기존 행 검색: 같은 ticker + source
    all_rows = ws.get_all_values()
    target_row_idx = None
    for i, row in enumerate(all_rows[1:], 2):
        if len(row) >= 2 and row[0] == ticker and row[1] == source:
            target_row_idx = i
            break

    # 행 데이터 구성
    row_data = [""] * len(HEADERS)
    row_data[0] = ticker
    row_data[1] = source
    row_data[2] = as_of

    for key, val in data.items():
        if key in HEADERS:
            idx = HEADERS.index(key)
            row_data[idx] = val if val is not None else ""

    if target_row_idx:
        # 기존 행의 비어있지 않은 값은 유지하면서 새 값으로 병합
        existing_row = all_rows[target_row_idx - 1]  # 0-indexed
        for i in range(3, len(HEADERS)):
            if i < len(existing_row) and existing_row[i] and not row_data[i]:
                row_data[i] = existing_row[i]
        cell_range = f"A{target_row_idx}:{chr(64 + len(HEADERS))}{target_row_idx}"
        ws.update(range_name=cell_range, values=[row_data], value_input_option="RAW")
    else:
        ws.append_row(row_data, value_input_option="RAW")


def get_all_estimates(ticker: str = None) -> list[dict]:
    """로컬 JSONL에서 읽기"""
    if not JSONL_PATH.exists():
        return []
    records = []
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                if ticker is None or rec.get("ticker") == ticker:
                    records.append(rec)
            except Exception:
                pass
    return records
