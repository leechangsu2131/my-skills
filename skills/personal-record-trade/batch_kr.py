"""
한국 개별주 배치 파이프라인 실행 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from pipeline.cli import run_pipeline

KR_STOCKS = [
    ("000660", "SK하이닉스"),
    ("001450", "현대해상"),
    ("035420", "네이버"),
    ("267260", "현대일렉트릭"),
    ("461300", "아이스크림미디어"),
]

PERIODS = [
    (2025, "A"),
    (2026, "Q1"),
]

def main():
    total = len(KR_STOCKS) * len(PERIODS)
    done = 0
    
    for ticker, name in KR_STOCKS:
        for year, quarter in PERIODS:
            done += 1
            print(f"\n{'#'*60}")
            print(f"# [{done}/{total}] {name} ({ticker}) — {year} {quarter}")
            print(f"{'#'*60}")
            try:
                run_pipeline(ticker, year, quarter)
            except SystemExit:
                print(f"[건너뜀] {name} {year}{quarter} — 데이터 없음 또는 오류")
            except Exception as e:
                print(f"[오류] {name} {year}{quarter}: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ 한국 개별주 배치 완료! 총 {total}건 처리")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
