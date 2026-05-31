import json
from pathlib import Path
from typing import TypedDict, Optional

class IndustryContext(TypedDict):
    tam_current: Optional[float]
    tam_cagr: Optional[float]
    tam_5yr: Optional[float]
    peer_per: Optional[float]
    normal_per: Optional[float]
    wacc: Optional[float]
    market_share_current: Optional[float]
    competitive_note: str

class IndustryResearcher:
    def __init__(self, data_root_str: str = "data/valuation"):
        self.data_root = Path(data_root_str)

    def _get_context_path(self, ticker: str) -> Path:
        ticker_dir = self.data_root / ticker / "normalized"
        ticker_dir.mkdir(parents=True, exist_ok=True)
        return ticker_dir / "industry_context.json"

    def load_context(self, ticker: str) -> IndustryContext:
        """종목의 산업 컨텍스트를 로드합니다. 없으면 기본 빈 딕셔너리 구조를 반환합니다."""
        path = self._get_context_path(ticker)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data
            except Exception as e:
                print(f"Error reading context for {ticker}: {e}")
        
        # Default empty context
        return {
            "tam_current": None,
            "tam_cagr": None,
            "tam_5yr": None,
            "peer_per": None,
            "normal_per": None,
            "wacc": None,
            "market_share_current": None,
            "competitive_note": ""
        }

    def save_context(self, ticker: str, context: IndustryContext) -> bool:
        """입력받은 산업 컨텍스트 딕셔너리를 JSON으로 저장합니다."""
        path = self._get_context_path(ticker)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(context, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving context for {ticker}: {e}")
            return False
