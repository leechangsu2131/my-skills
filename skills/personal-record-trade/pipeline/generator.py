import os
import json

def save_valuation_data(ticker: str, market_data: dict, metrics_data: list):
    """
    수집 및 매핑된 데이터를 data/valuation/{ticker}/normalized/ 하위에 JSON으로 저장합니다.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "valuation", ticker, "normalized"))
    
    # 폴더가 없으면 생성
    os.makedirs(base_dir, exist_ok=True)
    
    market_path = os.path.join(base_dir, "market.json")
    metrics_path = os.path.join(base_dir, "metrics.json")
    
    # market.json 저장
    if market_data:
        with open(market_path, 'w', encoding='utf-8') as f:
            json.dump(market_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Market 데이터 저장 완료: {market_path}")
        
    # metrics.json 저장
    if metrics_data:
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Metrics 데이터 저장 완료: {metrics_path}")

if __name__ == "__main__":
    pass
