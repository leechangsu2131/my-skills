"""
main.py
───────
당근마켓 매물 자동 수집 시스템 — 메인 실행 스크립트.

사용법:
    python main.py                          # 전체 키워드 수집
    python main.py --keyword "레고 스파이크"  # 특정 키워드만
    python main.py --local-only             # 구글시트 업로드 안 함
    python main.py --dry-run                # 테스트 (앱 조작 안 함)
    python main.py --visible                # (기본) 폰 화면 표시
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Windows 콘솔 인코딩 (한글 깨짐 방지)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from collector.appium_driver import create_driver, quit_driver, load_config
from collector.daangn_app import DaangnApp
from collector.extractor import save_to_json, print_summary
from collector.models import Product
from storage.sqlite_db import DaangnDB


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="당근마켓 매물 자동 수집 시스템 (Appium 기반)"
    )
    parser.add_argument(
        "--keyword", "-k",
        help="특정 키워드만 검색 (지정하지 않으면 config.json의 전체 키워드)",
    )
    parser.add_argument(
        "--local-only", "-l",
        action="store_true",
        help="구글시트 업로드 없이 로컬 저장만",
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="테스트 실행 (실제 앱 조작 없이 설정만 확인)",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="SQLite DB 저장/중복 체크 생략",
    )
    return parser.parse_args()


def get_keywords(config: dict, override: str | None = None) -> list[str]:
    """사용할 키워드 목록을 결정한다."""
    if override:
        return [override]

    # 1순위: 구글시트의 키워드 시트 (--local-only가 아닐 때)
    # → main 흐름에서 처리

    # 2순위: config.json
    return config.get("keywords", [])


def run_dry_mode(config: dict, keywords: list[str]) -> None:
    """설정만 확인하는 건조 실행."""
    print("\n🧪 DRY RUN 모드 — 실제 앱 조작 없음\n")

    print("📋 설정 확인:")
    print(f"  키워드: {keywords}")

    appium_cfg = config.get("appium", {})
    print(f"  Appium: {appium_cfg.get('host')}:{appium_cfg.get('port')}")
    print(f"  앱 패키지: {appium_cfg.get('app_package')}")

    coll_cfg = config.get("collection", {})
    print(f"  최대 스크롤: {coll_cfg.get('max_scroll_count')}회")
    print(f"  스크롤 간격: {coll_cfg.get('scroll_pause_sec')}초")
    print(f"  키워드 간 대기: {coll_cfg.get('between_keyword_delay_sec')}초")
    print(f"  판매완료 제외: {coll_cfg.get('exclude_sold')}")
    print(f"  제외 키워드: {coll_cfg.get('exclude_keywords')}")

    out_cfg = config.get("output", {})
    print(f"  JSON 저장: {out_cfg.get('json_dir')}")
    print(f"  SQLite: {out_cfg.get('sqlite_path')}")
    print(f"  구글시트: {'활성' if out_cfg.get('upload_to_gsheet') else '비활성'}")

    # 더미 데이터로 저장 테스트
    dummy = Product(
        title="[테스트] 레고 스파이크 프라임",
        price=150000,
        price_text="150,000원",
        location="부산진구",
        time_text="방금 전",
        keyword="레고 스파이크",
    )
    save_to_json([dummy], out_cfg.get("json_dir", "data"), "test")
    print("\n✅ DRY RUN 완료 — 설정에 문제 없습니다.")


def main() -> None:
    args = parse_args()
    config = load_config()

    print("=" * 60)
    print("🥕 당근마켓 매물 자동 수집 시스템")
    print("=" * 60)

    keywords = get_keywords(config, args.keyword)
    if not keywords:
        print("❌ 키워드가 없습니다. config.json에 keywords를 추가해주세요.")
        sys.exit(1)

    # DRY RUN
    if args.dry_run:
        run_dry_mode(config, keywords)
        return

    # 출력 설정
    out_cfg = config.get("output", {})
    coll_cfg = config.get("collection", {})
    json_dir = out_cfg.get("json_dir", "data")
    use_gsheet = out_cfg.get("upload_to_gsheet", True) and not args.local_only

    # SQLite DB 초기화
    db = None
    if not args.no_db:
        db = DaangnDB(out_cfg.get("sqlite_path", "data/daangn.db"))
        stats = db.get_stats()
        print(f"📊 DB 현황: 총 {stats['total']}건")

    # 구글시트 연결
    gsheet = None
    if use_gsheet:
        try:
            from storage.gsheet import GSheetClient
            gsheet = GSheetClient()
            gsheet.connect()

            # 구글시트에서 키워드 읽기 시도
            sheet_keywords = gsheet.read_keywords()
            if sheet_keywords and not args.keyword:
                keywords = sheet_keywords
                print(f"📋 구글시트 키워드 사용: {keywords}")
        except Exception as e:
            print(f"⚠️ 구글시트 연결 실패 — 로컬 저장으로 전환: {e}")
            gsheet = None

    # Appium 드라이버 연결
    driver = create_driver()
    app = DaangnApp(driver, config)

    all_products: list[Product] = []

    try:
        for idx, keyword in enumerate(keywords):
            # 키워드 간 대기 (첫 번째 제외)
            if idx > 0:
                delay = coll_cfg.get("between_keyword_delay_sec", 10)
                print(f"\n⏳ 다음 키워드까지 {delay}초 대기...")
                time.sleep(delay)

            # 검색 및 수집
            products = app.search_and_collect(keyword)

            # 중복 제거 (SQLite)
            if db:
                products = db.filter_new(products)

            if not products:
                print(f"  ℹ️ [{keyword}] 새 매물 없음")
                continue

            # JSON 저장
            save_to_json(products, json_dir, keyword)

            # SQLite 저장
            if db:
                inserted = db.insert_products(products)
                db.log_collection(keyword, inserted)
                print(f"  💾 DB 저장: {inserted}건")

            # 구글시트 업로드
            if gsheet:
                try:
                    gsheet.upload_products(products)
                except Exception as e:
                    print(f"  ⚠️ 구글시트 업로드 실패: {e}")

            all_products.extend(products)

    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 정리
        quit_driver(driver)

        if db:
            # 대시보드 업데이트
            if gsheet:
                try:
                    gsheet.update_dashboard(db.get_stats())
                except Exception:
                    pass
            db.close()

    # 결과 출력
    print_summary(all_products)

    if all_products:
        print(f"\n✅ 수집 완료! 총 {len(all_products)}건")
        print(f"   JSON: {json_dir}/")
        if db:
            print(f"   DB: {out_cfg.get('sqlite_path', 'data/daangn.db')}")
        if gsheet:
            print(f"   구글시트: 업로드 완료")
    else:
        print("\n📭 새로 수집된 매물이 없습니다.")


if __name__ == "__main__":
    main()
