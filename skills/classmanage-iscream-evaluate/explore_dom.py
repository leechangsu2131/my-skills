"""
아이스크림 교과 평가 페이지 DOM 탐색 스크립트

CDP(Chrome DevTools Protocol)를 통해 실행 중인 Chrome에 연결하여
아이스크림 교과 평가 페이지의 DOM 구조를 분석합니다.

사용법:
    python explore_dom.py
    python explore_dom.py --url "https://www.i-scream.co.kr/user/subjectevaluation/SubjectEvaluation.do"
    python explore_dom.py --port 9222
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright, Page, Frame


# ─── 기본 설정 ───────────────────────────────────────────────
DEFAULT_CDP_PORT = 9222
DEFAULT_URL = "https://www.i-scream.co.kr/user/subjectevaluation/SubjectEvaluation.do"
SCREENSHOT_PATH = Path(__file__).parent / "iscream_dom_screenshot.png"
HTML_DUMP_PATH = Path(__file__).parent / "iscream_dom_dump.html"


async def find_iscream_page(browser) -> Page | None:
    """브라우저의 모든 컨텍스트/페이지에서 아이스크림 관련 페이지를 탐색합니다."""
    print("\n🔍 아이스크림 관련 페이지 탐색 중...")

    for ctx_idx, context in enumerate(browser.contexts):
        for page_idx, page in enumerate(context.pages):
            url = page.url
            title = await page.title()
            print(f"  📄 컨텍스트[{ctx_idx}] 페이지[{page_idx}]: {title}")
            print(f"     URL: {url}")

            # URL에 아이스크림 또는 교과평가 관련 키워드가 포함되어 있는지 확인
            url_lower = url.lower()
            if "i-scream" in url_lower or "iscream" in url_lower or "subjectevaluation" in url_lower:
                print(f"  ✅ 아이스크림 페이지 발견!")
                return page

    print("  ⚠️ 아이스크림 관련 페이지를 찾지 못했습니다.")
    return None


async def extract_elements_from_frame(frame: Frame, depth: int = 0) -> dict:
    """프레임에서 주요 인터랙티브 요소들을 추출합니다 (재귀적으로 하위 프레임도 탐색)."""
    indent = "  " * (depth + 1)
    frame_name = frame.name or "(이름 없음)"
    frame_url = frame.url
    print(f"{indent}🖼️  프레임: {frame_name} | URL: {frame_url[:80]}...")

    result = {
        "frame_name": frame_name,
        "frame_url": frame_url,
        "selects": [],
        "inputs": [],
        "textareas": [],
        "buttons": [],
        "iframes": [],
        "forms": [],
        "child_frames": [],
    }

    # ─── <select> 드롭다운 요소 ─────────────────────────────
    try:
        selects = await frame.query_selector_all("select")
        for sel in selects:
            info = {
                "tag": "select",
                "id": await sel.get_attribute("id") or "",
                "name": await sel.get_attribute("name") or "",
                "class": await sel.get_attribute("class") or "",
                "options": [],
            }
            options = await sel.query_selector_all("option")
            for opt in options:
                opt_text = (await opt.inner_text()).strip()
                opt_value = await opt.get_attribute("value") or ""
                info["options"].append({"text": opt_text, "value": opt_value})
            result["selects"].append(info)
        if selects:
            print(f"{indent}  📋 <select> 요소: {len(selects)}개 발견")
    except Exception as e:
        print(f"{indent}  ⚠️ <select> 추출 오류: {e}")

    # ─── <input> 입력 요소 ───────────────────────────────────
    try:
        inputs = await frame.query_selector_all("input")
        for inp in inputs:
            info = {
                "tag": "input",
                "type": await inp.get_attribute("type") or "text",
                "id": await inp.get_attribute("id") or "",
                "name": await inp.get_attribute("name") or "",
                "class": await inp.get_attribute("class") or "",
                "placeholder": await inp.get_attribute("placeholder") or "",
                "value": await inp.get_attribute("value") or "",
            }
            result["inputs"].append(info)
        if inputs:
            print(f"{indent}  ✏️  <input> 요소: {len(inputs)}개 발견")
    except Exception as e:
        print(f"{indent}  ⚠️ <input> 추출 오류: {e}")

    # ─── <textarea> 텍스트 영역 ──────────────────────────────
    try:
        textareas = await frame.query_selector_all("textarea")
        for ta in textareas:
            info = {
                "tag": "textarea",
                "id": await ta.get_attribute("id") or "",
                "name": await ta.get_attribute("name") or "",
                "class": await ta.get_attribute("class") or "",
                "placeholder": await ta.get_attribute("placeholder") or "",
                "value": (await ta.inner_text()).strip()[:100],  # 내용 미리보기 (100자 제한)
            }
            result["textareas"].append(info)
        if textareas:
            print(f"{indent}  📝 <textarea> 요소: {len(textareas)}개 발견")
    except Exception as e:
        print(f"{indent}  ⚠️ <textarea> 추출 오류: {e}")

    # ─── <button> 버튼 요소 ──────────────────────────────────
    try:
        buttons = await frame.query_selector_all("button")
        for btn in buttons:
            info = {
                "tag": "button",
                "type": await btn.get_attribute("type") or "",
                "id": await btn.get_attribute("id") or "",
                "class": await btn.get_attribute("class") or "",
                "text": (await btn.inner_text()).strip()[:50],
                "onclick": await btn.get_attribute("onclick") or "",
            }
            result["buttons"].append(info)

        # input[type="button"] 및 input[type="submit"]도 포함
        input_buttons = await frame.query_selector_all('input[type="button"], input[type="submit"]')
        for btn in input_buttons:
            info = {
                "tag": "input-button",
                "type": await btn.get_attribute("type") or "",
                "id": await btn.get_attribute("id") or "",
                "class": await btn.get_attribute("class") or "",
                "value": await btn.get_attribute("value") or "",
                "onclick": await btn.get_attribute("onclick") or "",
            }
            result["buttons"].append(info)

        if result["buttons"]:
            print(f"{indent}  🔘 <button> 요소: {len(result['buttons'])}개 발견")
    except Exception as e:
        print(f"{indent}  ⚠️ <button> 추출 오류: {e}")

    # ─── <iframe> 요소 ───────────────────────────────────────
    try:
        iframes = await frame.query_selector_all("iframe")
        for ifr in iframes:
            info = {
                "tag": "iframe",
                "id": await ifr.get_attribute("id") or "",
                "name": await ifr.get_attribute("name") or "",
                "src": await ifr.get_attribute("src") or "",
                "class": await ifr.get_attribute("class") or "",
            }
            result["iframes"].append(info)
        if iframes:
            print(f"{indent}  🪟 <iframe> 요소: {len(iframes)}개 발견")
    except Exception as e:
        print(f"{indent}  ⚠️ <iframe> 추출 오류: {e}")

    # ─── <form> 폼 요소 ──────────────────────────────────────
    try:
        forms = await frame.query_selector_all("form")
        for form in forms:
            info = {
                "tag": "form",
                "id": await form.get_attribute("id") or "",
                "name": await form.get_attribute("name") or "",
                "action": await form.get_attribute("action") or "",
                "method": await form.get_attribute("method") or "",
                "class": await form.get_attribute("class") or "",
            }
            result["forms"].append(info)
        if forms:
            print(f"{indent}  📄 <form> 요소: {len(forms)}개 발견")
    except Exception as e:
        print(f"{indent}  ⚠️ <form> 추출 오류: {e}")

    # ─── 하위 프레임 재귀 탐색 ───────────────────────────────
    for child_frame in frame.child_frames:
        child_result = await extract_elements_from_frame(child_frame, depth + 1)
        result["child_frames"].append(child_result)

    return result


def print_summary(data: dict, depth: int = 0):
    """추출된 요소들의 요약을 출력합니다."""
    indent = "  " * depth
    frame_label = data.get("frame_name", "(메인)")

    total = (
        len(data["selects"])
        + len(data["inputs"])
        + len(data["textareas"])
        + len(data["buttons"])
        + len(data["iframes"])
        + len(data["forms"])
    )

    if total > 0 or depth == 0:
        print(f"\n{indent}{'═' * 60}")
        print(f"{indent}📊 프레임 요약: {frame_label}")
        print(f"{indent}{'─' * 60}")

    # select 요약
    for sel in data["selects"]:
        selector = _build_selector(sel)
        opt_count = len(sel["options"])
        opt_preview = ", ".join(o["text"] for o in sel["options"][:5])
        if len(sel["options"]) > 5:
            opt_preview += f" ... (+{len(sel['options']) - 5}개)"
        print(f"{indent}  📋 SELECT {selector}")
        print(f"{indent}     옵션 ({opt_count}개): {opt_preview}")

    # input 요약
    for inp in data["inputs"]:
        inp_type = inp.get("type", "text")
        # hidden 필드는 간략하게 표시
        if inp_type == "hidden":
            continue
        selector = _build_selector(inp)
        print(f"{indent}  ✏️  INPUT[{inp_type}] {selector}")
        if inp.get("placeholder"):
            print(f"{indent}     placeholder: {inp['placeholder']}")

    # textarea 요약
    for ta in data["textareas"]:
        selector = _build_selector(ta)
        print(f"{indent}  📝 TEXTAREA {selector}")
        if ta.get("value"):
            print(f"{indent}     내용 미리보기: {ta['value'][:60]}...")

    # button 요약
    for btn in data["buttons"]:
        selector = _build_selector(btn)
        label = btn.get("text") or btn.get("value") or "(라벨 없음)"
        print(f"{indent}  🔘 BUTTON {selector} → \"{label}\"")

    # iframe 요약
    for ifr in data["iframes"]:
        selector = _build_selector(ifr)
        print(f"{indent}  🪟 IFRAME {selector}")
        print(f"{indent}     src: {ifr.get('src', '(없음)')[:80]}")

    # form 요약
    for form in data["forms"]:
        selector = _build_selector(form)
        action = form.get("action") or "(없음)"
        method = (form.get("method") or "GET").upper()
        print(f"{indent}  📄 FORM {selector} → {method} {action}")

    # 하위 프레임 재귀 출력
    for child in data.get("child_frames", []):
        print_summary(child, depth + 1)


def _build_selector(el: dict) -> str:
    """요소 정보로부터 CSS 선택자 힌트를 생성합니다."""
    parts = []
    if el.get("id"):
        parts.append(f"#{el['id']}")
    if el.get("name"):
        parts.append(f"[name=\"{el['name']}\"]")
    if el.get("class"):
        classes = el["class"].strip().split()[:3]  # 클래스 최대 3개
        parts.append("." + ".".join(classes))
    return " ".join(parts) if parts else "(선택자 없음)"


async def main():
    """메인 실행 함수"""
    # ─── 명령줄 인수 파싱 ────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="아이스크림 교과 평가 페이지 DOM 탐색 도구"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="탐색할 URL (지정하면 해당 URL로 이동 후 분석)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_CDP_PORT,
        help=f"CDP 원격 디버깅 포트 (기본값: {DEFAULT_CDP_PORT})",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  🔬 아이스크림 교과 평가 - DOM 탐색 도구")
    print("=" * 60)
    print(f"\n📡 CDP 포트: {args.port}")

    async with async_playwright() as pw:
        # ─── Chrome CDP 연결 ─────────────────────────────────
        print(f"\n🔗 Chrome에 CDP로 연결 중... (localhost:{args.port})")
        try:
            browser = await pw.chromium.connect_over_cdp(f"http://localhost:{args.port}")
            print("✅ Chrome 연결 성공!")
        except Exception as e:
            print(f"\n❌ Chrome 연결 실패: {e}")
            print(f"\n💡 해결 방법:")
            print(f"   1. launch_chrome_iscream.bat을 먼저 실행하세요.")
            print(f"   2. 기존 Chrome 창을 모두 닫고 다시 시도하세요.")
            print(f"   3. CDP 포트({args.port})가 올바른지 확인하세요.")
            sys.exit(1)

        # ─── 대상 페이지 찾기 또는 이동 ─────────────────────
        target_page = None

        if args.url:
            # URL이 지정된 경우: 첫 번째 페이지에서 해당 URL로 이동
            print(f"\n🌐 지정된 URL로 이동합니다: {args.url}")
            if browser.contexts and browser.contexts[0].pages:
                target_page = browser.contexts[0].pages[0]
            else:
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                target_page = await context.new_page()
            await target_page.goto(args.url, wait_until="networkidle", timeout=30000)
            print("✅ 페이지 로딩 완료!")
        else:
            # URL 미지정: 기존 열린 페이지에서 아이스크림 페이지 검색
            target_page = await find_iscream_page(browser)

            if target_page is None:
                # 아이스크림 페이지가 없으면 기본 URL로 이동
                print(f"\n🌐 기본 URL로 이동합니다: {DEFAULT_URL}")
                if browser.contexts and browser.contexts[0].pages:
                    target_page = browser.contexts[0].pages[0]
                else:
                    context = browser.contexts[0] if browser.contexts else await browser.new_context()
                    target_page = await context.new_page()
                await target_page.goto(DEFAULT_URL, wait_until="networkidle", timeout=30000)
                print("✅ 페이지 로딩 완료!")

        # ─── 현재 페이지 정보 출력 ───────────────────────────
        page_title = await target_page.title()
        page_url = target_page.url
        print(f"\n📄 대상 페이지: {page_title}")
        print(f"   URL: {page_url}")

        # ─── 스크린샷 저장 ───────────────────────────────────
        print(f"\n📸 스크린샷 저장 중... → {SCREENSHOT_PATH.name}")
        await target_page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
        print(f"✅ 스크린샷 저장 완료: {SCREENSHOT_PATH}")

        # ─── HTML 덤프 저장 ──────────────────────────────────
        print(f"\n💾 HTML 덤프 저장 중... → {HTML_DUMP_PATH.name}")
        html_content = await target_page.content()
        HTML_DUMP_PATH.write_text(html_content, encoding="utf-8")
        print(f"✅ HTML 덤프 저장 완료: {HTML_DUMP_PATH} ({len(html_content):,} bytes)")

        # ─── DOM 요소 추출 (메인 프레임 + 하위 프레임 재귀) ──
        print(f"\n🔍 DOM 인터랙티브 요소 추출 중...")
        dom_data = await extract_elements_from_frame(target_page.main_frame, depth=0)

        # ─── 요약 출력 ───────────────────────────────────────
        print("\n\n" + "=" * 60)
        print("  📊 DOM 인터랙티브 요소 요약")
        print("=" * 60)
        print_summary(dom_data, depth=0)

        # ─── 전체 카운트 출력 ────────────────────────────────
        total_counts = _count_all(dom_data)
        print(f"\n\n{'═' * 60}")
        print(f"  📈 전체 통계")
        print(f"{'─' * 60}")
        print(f"  📋 SELECT 드롭다운: {total_counts['selects']}개")
        print(f"  ✏️  INPUT 입력 필드: {total_counts['inputs']}개")
        print(f"  📝 TEXTAREA 텍스트 영역: {total_counts['textareas']}개")
        print(f"  🔘 BUTTON 버튼: {total_counts['buttons']}개")
        print(f"  🪟 IFRAME 프레임: {total_counts['iframes']}개")
        print(f"  📄 FORM 폼: {total_counts['forms']}개")
        total = sum(total_counts.values())
        print(f"{'─' * 60}")
        print(f"  합계: {total}개 인터랙티브 요소")
        print(f"{'═' * 60}")

        # ─── JSON 데이터 저장 ────────────────────────────────
        json_path = Path(__file__).parent / "iscream_dom_elements.json"
        json_path.write_text(
            json.dumps(dom_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n💾 요소 데이터 JSON 저장: {json_path}")

        print("\n✅ DOM 탐색 완료!")


def _count_all(data: dict) -> dict:
    """모든 프레임의 요소 수를 재귀적으로 합산합니다."""
    counts = {
        "selects": len(data.get("selects", [])),
        "inputs": len(data.get("inputs", [])),
        "textareas": len(data.get("textareas", [])),
        "buttons": len(data.get("buttons", [])),
        "iframes": len(data.get("iframes", [])),
        "forms": len(data.get("forms", [])),
    }
    for child in data.get("child_frames", []):
        child_counts = _count_all(child)
        for key in counts:
            counts[key] += child_counts[key]
    return counts


if __name__ == "__main__":
    asyncio.run(main())
