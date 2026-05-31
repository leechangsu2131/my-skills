import os
import json
import sys

# Windows cp949 인코딩 오류 방지
if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

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
        
    # metrics.json 병합 저장
    if metrics_data:
        existing_metrics = []
        if os.path.exists(metrics_path):
            with open(metrics_path, 'r', encoding='utf-8') as f:
                try:
                    existing_metrics = json.load(f)
                except json.JSONDecodeError:
                    existing_metrics = []
                    
        # 기존 데이터를 딕셔너리로 (period + metric_key 기준)
        metrics_dict = {f"{item['period']}_{item['metric_key']}": item for item in existing_metrics}
        
        # 새 데이터 덮어쓰기/추가
        for item in metrics_data:
            key = f"{item['period']}_{item['metric_key']}"
            metrics_dict[key] = item
            
        final_metrics = list(metrics_dict.values())
        
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(final_metrics, f, ensure_ascii=False, indent=2)
        print(f"✅ Metrics 데이터 병합 저장 완료: {metrics_path} (총 {len(final_metrics)}개 항목)")

if __name__ == "__main__":
    pass
