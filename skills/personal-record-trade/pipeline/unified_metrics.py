import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "data" / "metric_config.json"
JSONL_PATH = ROOT / "data" / "estimates_raw.jsonl"

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_estimates(ticker: str) -> dict:
    """Reads estimates_raw.jsonl and returns a dict mapping source -> data."""
    if not JSONL_PATH.exists():
        return {}
        
    records = {}
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                rec = json.loads(line)
                if rec.get("ticker") == ticker:
                    source = rec.get("source")
                    if source:
                        records[source] = rec
            except Exception:
                pass
    return records

def get_unified_metrics(ticker: str) -> dict:
    """
    Applies the Concept Map priority (Fallback Strategy) to combine metrics from different sources.
    Returns a unified dictionary.
    """
    config = load_config()
    source_data = load_estimates(ticker)
    
    unified = {"ticker": ticker}
    
    for category, metrics in config.items():
        for metric, priorities in metrics.items():
            unified[metric] = None
            # Evaluate by priority
            for source in priorities:
                if source in source_data:
                    val = source_data[source].get(metric)
                    if val is not None and str(val).strip() != "":
                        unified[metric] = val
                        unified[f"{metric}_source"] = source
                        break
                        
    return unified

if __name__ == "__main__":
    import sys
    # Windows cp949 fix
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    unified_data = get_unified_metrics(ticker)
    print(json.dumps(unified_data, indent=4, ensure_ascii=False))
