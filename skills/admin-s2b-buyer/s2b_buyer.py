"""
S2B 학교장터 자동 구매 시스템 통합 스크립트

사용법:
    python s2b_buyer.py items.csv
    python s2b_buyer.py "list/자투리공간 체육물품 구입내역(화천초).xlsx"
    python s2b_buyer.py items.csv --dry-run
    python s2b_buyer.py items.csv --headless
    python s2b_buyer.py items.csv --report 결과.xlsx   ← 리포트 파일명 직접 지정
"""

import asyncio
import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# 내부 모듈
from s2b_login import login as s2b_login
from s2b_search import search_items
from s2b_cart import add_to_cart
from s2b_report import save_report   # ← 추가
from s2b_excel import load_purchase_items

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace') if hasattr(sys, 'stdout') and hasattr(sys.stdout, 'buffer') else sys.stdout
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace') if hasattr(sys, 'stderr') and hasattr(sys.stderr, 'buffer') else sys.stderr

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _detail_link(item_id):
    return f"https://www.s2b.kr/S2BNCustomer/rema100.do?forwardName=detail&f_re_estimate_code={item_id}"


async def process_items(input_path, dry_run=False, headless=False, report_path=None):
    """
    CSV/XLSX 파일을 읽어 각 물품을 S2B 견적서에 담습니다.
    S2B번호가 있으면 직접 담고, 없으면 품목명으로 검색한 첫 결과를 사용합니다.
    완료 후 Excel 결과 리포트를 저장합니다.
    """
    if not os.path.exists(input_path):
        print(f"❌ 파일을 찾을 수 없습니다: {input_path}")
        return False

    try:
        items_to_buy = load_purchase_items(input_path)
    except Exception as e:
        print(f"❌ 구매 목록 읽기 실패: {e}")
        return False

    if not items_to_buy:
        print("⚠ 구매할 물품 목록이 비어있습니다.")
        return False

    direct_count = sum(1 for item in items_to_buy if item.get('s2b_id'))
    search_count = len(items_to_buy) - direct_count
    print(f"📋 총 {len(items_to_buy)}개의 품목을 장바구니(견적서)에 담습니다.")
    print(f"   S2B번호 직접 담기: {direct_count}건 / 품목명 검색: {search_count}건")

    load_dotenv(os.path.join(SCRIPT_DIR, '.env'))
    uid = os.getenv('S2B_USER_ID')
    pwd = os.getenv('S2B_USER_PW')

    if not uid or not pwd:
        print("❌ S2B 계정 정보가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return False

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ playwright가 설치되지 않았습니다. (pip install playwright)")
        return False

    print("=" * 60)
    print("🏫 S2B 학교장터 자동 구매 봇 시작")
    if dry_run:
        print("   ※ DRY-RUN 모드: 실제 장바구니에 담지 않습니다.")
    print("=" * 60)

    # ── 결과 수집 리스트 ────────────────────────────────
    purchase_results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=300)
        context = await browser.new_context(viewport={'width': 1280, 'height': 900}, locale='ko-KR')
        page = await context.new_page()

        # 1. 로그인
        print("\n[STEP 1] 로그인 진행...")
        login_success = await s2b_login(page, uid, pwd)
        if not login_success:
            print("❌ 로그인에 실패하여 작업을 중단합니다.")
            await browser.close()
            return False

        # 2. 아이템별 처리
        print("\n[STEP 2] 품목 검색 및 견적서 담기...")
        for idx, item in enumerate(items_to_buy):
            print("-" * 60)
            print(f"[{idx+1}/{len(items_to_buy)}] {item['name']} (수량: {item['quantity']})")

            result_entry = {
                'request_name': item['name'],
                'quantity': item['quantity'],
                'selected_title': '',
                'selected_id': '',
                'image': '',
                'price': item.get('unit_price', ''),
                'link': '',
                'source_row': item.get('source_row', ''),
                'source_code': item.get('raw_code', ''),
                'success': False,
                'fail_reason': '',
                'processed_at': datetime.now(),
            }

            # 엑셀에 S2B번호가 있으면 검색 없이 상세 URL로 바로 담습니다.
            if item.get('s2b_id'):
                target_item = {
                    'id': item['s2b_id'],
                    'title': item['name'],
                    'price': item.get('unit_price', ''),
                    'image': '',
                    'link': _detail_link(item['s2b_id']),
                }
                print(f"  👉 엑셀 S2B번호 사용: [{target_item['id']}]")
            else:
                search_results = await search_items(page, item['name'])
                if not search_results:
                    msg = f"'{item['name']}' 검색 결과 없음"
                    print(f"  ⚠ {msg}. 건너뜁니다.")
                    result_entry['fail_reason'] = msg
                    purchase_results.append(result_entry)
                    continue

                # 첫 번째 결과 선택
                target_item = search_results[0]
                print(f"  👉 검색 첫 결과 선택: [{target_item['id']}] {target_item['title']}")

            result_entry['selected_title'] = target_item.get('title', '')
            result_entry['selected_id'] = target_item.get('id', '')
            result_entry['image'] = target_item.get('image', '')
            result_entry['price'] = target_item.get('price', '') or item.get('unit_price', '')
            result_entry['link'] = target_item.get('link', '') or _detail_link(target_item.get('id', ''))

            if not result_entry['selected_id']:
                result_entry['fail_reason'] = "물품번호 없음"
                purchase_results.append(result_entry)
                continue

            # 장바구니 담기
            added = await add_to_cart(
                page, target_item['id'],
                quantity=item['quantity'],
                dry_run=dry_run
            )

            result_entry['success']      = added
            result_entry['processed_at'] = datetime.now()
            if not added:
                result_entry['fail_reason'] = "견적서 담기 실패 (팝업/네트워크 오류)"

            purchase_results.append(result_entry)

            # 서버 과부하 방지
            await page.wait_for_timeout(2000)

        if not headless:
            await page.wait_for_timeout(3000)
        await browser.close()

    # ── 결과 요약 출력 ───────────────────────────────
    success_count = sum(1 for r in purchase_results if r['success'])
    fail_count    = len(purchase_results) - success_count

    print("=" * 60)
    print("🎉 작업 완료!")
    print(f"   성공: {success_count}건")
    print(f"   실패: {fail_count}건")
    print("=" * 60)

    # ── Excel 리포트 저장 ────────────────────────────
    if purchase_results:
        try:
            saved_path = save_report(purchase_results, output_path=report_path)
            print(f"\n📊 결과 리포트 저장 완료: {saved_path}")
        except ImportError as e:
            print(f"\n⚠ 리포트 저장 건너뜀: {e}")
        except Exception as e:
            print(f"\n❌ 리포트 저장 실패: {e}")

    return True


def main():
    parser = argparse.ArgumentParser(description='S2B 학교장터 자동 구매/장바구니 담기 봇')
    parser.add_argument('input_file',
                        help='구매할 품목 목록 CSV/XLSX 파일 경로')
    parser.add_argument('--dry-run', action='store_true',
                        help='실제 장바구니에 담지 않고 시뮬레이션만 수행')
    parser.add_argument('--headless', action='store_true',
                        help='브라우저 창을 띄우지 않고 백그라운드 실행')
    parser.add_argument('--report', metavar='XLSX_PATH', default=None,
                        help='결과 Excel 파일 저장 경로 (기본값: 자동 생성)')

    args = parser.parse_args()

    asyncio.run(process_items(
        args.input_file,
        dry_run=args.dry_run,
        headless=args.headless,
        report_path=args.report,
    ))


if __name__ == "__main__":
    main()
