#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
edufine_auto_approve.py
========================
경북교육청 업무포털(gbe.eduptl.kr)의 K-에듀파인 결재대기 문서를
자동으로 결재 처리하는 스크립트.

사전 조건:
  1. launch_chrome.bat 으로 Chrome을 원격 디버깅 모드(포트 9222)로 실행
  2. 사용자가 직접 공동인증서로 업무포털에 로그인 완료
  3. pip install playwright (playwright install 완료)

실행:
  python edufine_auto_approve.py                     # 결재대기 목록 확인 (dry-run)
  python edufine_auto_approve.py --apply             # 실제 결재 처리 (K-에듀파인 창 자동 열기)
  python edufine_auto_approve.py --tab sanctnWait    # 결재대기 처리 (기본)
  python edufine_auto_approve.py --tab dsplayWait    # 공람 대기 처리

안전 정책:
  - --apply 없이는 실제 창을 열지 않음 (dry-run)
  - 처리된 문서 목록은 result/ 폴더에 txt 파일로 저장
  - 결재 자체는 K-에듀파인에서 사용자가 직접 처리 (자동 결재 버튼 클릭 없음)
"""

import asyncio
import sys
import os
import time
import argparse
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# 설정값
# ─────────────────────────────────────────────────────────────────────────────
CDP_PORT = 9222
PORTAL_URL_PATTERN = "eduptl.kr"
RESULT_DIR = Path(__file__).parent / "result"
RESULT_DIR.mkdir(exist_ok=True)

TAB_MAP = {
    "sanctnWait": "결재대기",
    "dsplayWait": "공람대기",
    "sanctnView": "문서진행",
    "sendWait":   "발송대기",
}


# ─────────────────────────────────────────────────────────────────────────────
# 연결 유틸
# ─────────────────────────────────────────────────────────────────────────────
async def connect_to_portal():
    """Chrome CDP 연결 및 업무포털 탭 반환."""
    try:
        p = await async_playwright().start()
        browser = await p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
    except Exception as e:
        print(f"[오류] Chrome 연결 실패: {e}")
        print(f"  → launch_chrome.bat 으로 Chrome을 먼저 실행해 주세요.")
        sys.exit(1)

    target_page = None
    for ctx in browser.contexts:
        for page in ctx.pages:
            if PORTAL_URL_PATTERN in page.url:
                target_page = page
                break
        if target_page:
            break

    if not target_page:
        print("[오류] 업무포털 탭을 찾을 수 없습니다.")
        print("  → Chrome에서 https://gbe.eduptl.kr 에 로그인해 주세요.")
        await p.stop()
        sys.exit(1)

    return p, browser, target_page


# ─────────────────────────────────────────────────────────────────────────────
# kedufine 탭 이동 및 목록 수집
# ─────────────────────────────────────────────────────────────────────────────
async def navigate_to_tab(page, tab_key: str) -> bool:
    """포털 메인에서 K-에듀파인 문서함 탭 클릭."""
    tab_name = TAB_MAP.get(tab_key, tab_key)
    frame0 = page.frames[0]

    # 탭 링크 찾기
    for link in await frame0.locator("a").all():
        try:
            text = (await link.inner_text()).strip()
            if text == tab_name:
                await link.click()
                await page.wait_for_timeout(2000)
                print(f"[네비게이션] '{tab_name}' 탭 클릭 완료")
                return True
        except:
            pass

    print(f"[경고] '{tab_name}' 탭을 찾지 못했습니다.")
    return False


async def get_document_list(page) -> list:
    """kedufine iframe에서 결재대기 문서 목록 수집."""
    docs = []

    # kedufine iframe 찾기
    kedu_frame = None
    for f in page.frames:
        if f.name == "kedufine":
            kedu_frame = f
            break

    if not kedu_frame:
        print("[경고] kedufine iframe을 찾지 못했습니다.")
        return docs

    # TR 행 순회
    rows = await kedu_frame.locator("tr").all()
    for row in rows:
        try:
            link = row.locator("a.ellipsis")
            if await link.count() == 0:
                continue

            title = (await link.first.get_attribute("title") or "").strip()
            if not title:
                title = (await link.first.inner_text()).strip()

            writer_el = row.locator("td.writer")
            writer = ""
            if await writer_el.count() > 0:
                writer = (await writer_el.first.inner_text()).strip()

            date_el = row.locator("td.date")
            doc_date = ""
            if await date_el.count() > 0:
                doc_date = (await date_el.first.inner_text()).strip()

            docs.append({
                "title": title,
                "writer": writer,
                "date": doc_date,
            })
        except:
            pass

    return docs


# ─────────────────────────────────────────────────────────────────────────────
# 결과 저장
# ─────────────────────────────────────────────────────────────────────────────
def save_result(docs: list, tab_key: str, mode: str = "dry-run"):
    """처리된 문서 목록을 txt 파일로 저장."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tab_name = TAB_MAP.get(tab_key, tab_key)
    filename = RESULT_DIR / f"edufine_{tab_key}_{timestamp}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"K-에듀파인 {tab_name} 문서 목록\n")
        f.write(f"수집 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"처리 모드: {mode}\n")
        f.write(f"문서 수: {len(docs)}건\n")
        f.write("=" * 60 + "\n\n")

        for i, doc in enumerate(docs, 1):
            f.write(f"{i:3}. [{doc['date']}] {doc['title']} ({doc['writer']})\n")

    print(f"\n[저장] 문서 목록 저장 완료: {filename}")
    return filename


# ─────────────────────────────────────────────────────────────────────────────
# K-에듀파인 창 열기 (결재 처리용)
# ─────────────────────────────────────────────────────────────────────────────
async def open_kedufine_approval(page, tab_key: str):
    """
    포털의 결재(긴급) 또는 해당 링크를 클릭하여 K-에듀파인 새 창을 엽니다.
    보안 모듈 체크가 필요하므로 실제 결재는 사용자가 직접 수행합니다.
    """
    frame0 = page.frames[0]

    # 해당 탭 링크 URL 매핑
    link_url_map = {
        "sanctnWait": "sanctnWait",
        "dsplayWait": "dsplayWait",
        "sanctnView": "sanctnView",
        "sendWait":   "sendWait",
    }
    link_param = link_url_map.get(tab_key, tab_key)

    # 포털 위젯의 직접 링크 클릭 (예: 결재(긴급) → klef.gbe.kr/portal/link.do?link=sanctnWait)
    target_href = f"link={link_param}"
    portal_link = None
    for link in await frame0.locator("a").all():
        try:
            href = await link.get_attribute("href") or ""
            if target_href in href:
                portal_link = link
                break
        except:
            pass

    if not portal_link:
        print(f"[경고] '{tab_key}' 포털 링크를 찾지 못했습니다.")
        return None

    print(f"[안내] K-에듀파인 결재 창을 엽니다...")
    print(f"  → 보안 모듈이 설치된 경우 자동으로 K-에듀파인이 열립니다.")
    print(f"  → 열리지 않으면 포털에서 직접 K-에듀파인을 클릭해 주세요.")

    try:
        async with page.context.expect_page(timeout=15000) as new_page_info:
            await portal_link.click()

        kedu_page = await new_page_info.value
        await kedu_page.wait_for_timeout(5000)

        final_url = kedu_page.url
        if "install.html" in final_url:
            print("[경고] K-에듀파인 보안 모듈 체크 페이지로 이동됨.")
            print("  → 필수 보안 프로그램(KCaseAgent, MarkAnyDRM 등)이 설치/실행 중인지 확인하세요.")
            print("  → 수동으로 포털에서 K-에듀파인을 열어 결재를 처리해 주세요.")
            await kedu_page.close()
            return None

        print(f"[성공] K-에듀파인 창 열림: {final_url}")
        print(f"  → 브라우저에서 결재 대기 문서를 직접 결재해 주세요.")
        return kedu_page

    except Exception as e:
        print(f"[오류] K-에듀파인 창 열기 실패: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────────────────────
async def main(args):
    tab_key = args.tab
    tab_name = TAB_MAP.get(tab_key, tab_key)
    apply_mode = args.apply

    print(f"\n{'='*60}")
    print(f"  K-에듀파인 {tab_name} 자동화 봇")
    print(f"  모드: {'실행 (--apply)' if apply_mode else 'Dry-run (확인만)'}")
    print(f"{'='*60}\n")

    p, browser, portal_page = await connect_to_portal()

    try:
        await portal_page.bring_to_front()
        print(f"[연결] 업무포털 탭 확인: {await portal_page.title()}")

        # 1) 결재대기 탭으로 이동
        await navigate_to_tab(portal_page, tab_key)

        # 2) 문서 목록 수집
        docs = await get_document_list(portal_page)
        print(f"\n[수집] {tab_name} 문서 {len(docs)}건 발견:")
        for i, doc in enumerate(docs, 1):
            print(f"  {i:3}. [{doc['date']}] {doc['title']} ({doc['writer']})")

        if not docs:
            print(f"\n[안내] {tab_name} 문서가 없습니다.")
            await p.stop()
            return

        # 3) 결과 파일 저장 (항상)
        mode_str = "apply" if apply_mode else "dry-run"
        saved_path = save_result(docs, tab_key, mode=mode_str)

        # 4) 실제 처리 (--apply 시)
        if apply_mode:
            print(f"\n[실행] K-에듀파인 {tab_name} 창을 열어 결재를 진행합니다...")
            kedu_page = await open_kedufine_approval(portal_page, tab_key)

            if kedu_page:
                print(f"\n[안내] K-에듀파인이 열렸습니다.")
                print(f"  → 결재 대기 문서를 확인하고 직접 결재해 주세요.")
                print(f"  → 스크립트는 창을 유지합니다. 종료하려면 Ctrl+C를 누르세요.")
                try:
                    # 창이 닫힐 때까지 대기
                    while True:
                        try:
                            await kedu_page.title()
                            await asyncio.sleep(5)
                        except:
                            print("[안내] K-에듀파인 창이 닫혔습니다.")
                            break
                except KeyboardInterrupt:
                    print("\n[종료] 사용자가 종료했습니다.")
        else:
            print(f"\n[Dry-run] 실제 처리를 하려면 --apply 옵션을 추가하세요:")
            print(f"  python edufine_auto_approve.py --apply --tab {tab_key}")

    finally:
        await p.stop()

    print(f"\n[완료] 처리 완료. 목록은 {saved_path} 에 저장되었습니다.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="K-에듀파인 결재대기 자동화 봇")
    parser.add_argument("--apply", action="store_true", help="실제 결재 창 열기 (기본: dry-run)")
    parser.add_argument("--tab", default="sanctnWait",
                        choices=list(TAB_MAP.keys()),
                        help="처리할 탭 (기본: sanctnWait=결재대기)")
    args = parser.parse_args()
    asyncio.run(main(args))
