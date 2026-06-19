#!/usr/bin/env python
"""Assist K-에듀파인 개산급정산등록 row entry through an existing Chrome session."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("NODE_OPTIONS", "--no-deprecation")

from playwright.async_api import Page, async_playwright


DEFAULT_START_DATE = "2026-03-01"
DEFAULT_CDP_URL = "http://127.0.0.1:9222"


def load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data.get("receipts", data if isinstance(data, list) else [])
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    raise ValueError("Rows file must be .json or .csv")


def normalize(row: dict[str, Any]) -> dict[str, str]:
    return {
        "date": str(row.get("date") or row.get("사용일자") or ""),
        "vendor": str(row.get("vendor") or row.get("사용업체명") or ""),
        "amount": str(row.get("amount") or row.get("사용금액") or "").replace(",", ""),
        "evidence_type": str(row.get("evidence_type") or row.get("증빙구분") or "전산자료"),
        "usage": str(row.get("usage") or row.get("사용내역") or ""),
    }


async def visible_click(page: Page, text: str, timeout: int = 4000) -> bool:
    deadline = asyncio.get_running_loop().time() + timeout / 1000
    selector = f"text='{text}'"
    while asyncio.get_running_loop().time() < deadline:
        for frame in [page] + page.frames:
            try:
                for loc in await frame.locator(selector).all():
                    box = await loc.bounding_box()
                    if box and box["width"] > 0 and box["height"] > 0 and box["x"] >= 0 and box["y"] >= 0:
                        await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                        await page.wait_for_timeout(500)
                        return True
            except Exception:
                continue
        await page.wait_for_timeout(250)
    return False


async def click_locator_dispatch(locator, timeout: int = 3000) -> bool:
    if await locator.count() == 0:
        return False
    target = locator.first
    try:
        await target.click(force=True, timeout=timeout)
    except Exception:
        await target.evaluate(
            """el => {
              el.dispatchEvent(new MouseEvent('mousedown', {bubbles:true, cancelable:true, view:window}));
              el.dispatchEvent(new MouseEvent('mouseup', {bubbles:true, cancelable:true, view:window}));
              el.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
            }"""
        )
    return True


async def close_notice_popups(page: Page) -> None:
    """Close sequential notice popups that leave Nexacro modal overlays."""
    for _ in range(8):
        popup_ids = await page.evaluate(
            """() => Array.from(document.querySelectorAll('[id*="noticePopup"]'))
              .map(e => e.id)
              .filter(id => /noticePopup\\d+$/.test(id))"""
        )
        popup_ids = sorted(set(popup_ids))
        if not popup_ids:
            return

        closed = False
        for popup_id in popup_ids:
            base = "#" + popup_id.replace(".", "\\.")
            for suffix in [
                "\\.form\\.divPopupBottom\\.form\\.chkDay",
                "\\.form\\.divPopupBottom\\.form\\.btnClose",
                "\\.form\\.btnClose00",
            ]:
                selector = base + suffix
                try:
                    if await page.locator(selector).count() > 0:
                        await page.locator(selector).click(force=True, timeout=2000)
                        await page.wait_for_timeout(600)
                        closed = True
                except Exception:
                    continue
        if not closed:
            return
        await page.wait_for_timeout(800)


async def switch_to_school_accounting(page: Page) -> None:
    body = await page.locator("body").inner_text(timeout=3000)
    if "사업담당" in body and "품의/정산" in body:
        return

    comboedit = page.locator(
        "#mainframe\\.MainVFrameSet\\.TopFrame\\.form\\.cboJobList\\.comboedit"
    )
    await comboedit.click(force=True, timeout=5000)
    await page.wait_for_timeout(300)
    # Observed order: 업무관리, 지식관리, 학교회계, 재정분석, 서비스공통.
    for key in ["Home", "ArrowDown", "ArrowDown", "Enter"]:
        await page.keyboard.press(key)
        await page.wait_for_timeout(500)
    await page.wait_for_timeout(5000)


async def click_left_menu_row(page: Page, menu_text: str) -> bool:
    rows = await page.locator('[id*="gridMenu.body.gridrow"]').all()
    for row in rows:
        try:
            text = (await row.inner_text(timeout=500)).replace("\n", " ").strip()
            box = await row.bounding_box(timeout=500)
            if menu_text in text and box and box["width"] > 0 and box["height"] > 0:
                await row.click(force=True, timeout=3000)
                await page.wait_for_timeout(2500)
                return True
        except Exception:
            continue
    return False


async def set_search_date_and_query(page: Page, start_date: str) -> None:
    from_input = page.locator(
        '[id$="form.divWork.form.divSearch.form.calRecptDteFrom.calendaredit:input"]'
    ).first
    if await from_input.count() > 0:
        await from_input.click(force=True, timeout=3000)
        await from_input.fill(start_date, force=True)
        await page.wait_for_timeout(300)
    else:
        print("[WARN] Could not find the settlement start date input.")

    search_button = page.locator('[id$="form.divWork.form.divAuth.form.btnAuthS01"]').first
    if await click_locator_dispatch(search_button):
        await page.wait_for_timeout(2000)
    elif not await visible_click(page, "조회", timeout=3000):
        print("[WARN] Could not find the 조회 button.")


async def find_edufine_page(browser) -> Page | None:
    candidates: list[Page] = []
    for context in browser.contexts:
        for page in context.pages:
            title = ""
            try:
                title = await page.title()
            except Exception:
                pass
            url = page.url.lower()
            if "klef" in url or "에듀파인" in title or "edufine" in title.lower():
                candidates.append(page)
    return candidates[0] if candidates else None


async def page_summary(browser) -> str:
    lines: list[str] = []
    for context in browser.contexts:
        for page in context.pages:
            try:
                title = await page.title()
            except Exception:
                title = ""
            lines.append(f"- {title or '(no title)'} | {page.url}")
    return "\n".join(lines) if lines else "(no open pages)"


async def open_edufine_from_portal(browser) -> Page | None:
    for context in browser.contexts:
        for page in context.pages:
            title = ""
            try:
                title = await page.title()
            except Exception:
                pass
            url = page.url.lower()
            if "eduptl" not in url and "업무포털" not in title:
                continue

            await page.bring_to_front()
            try:
                loc = page.locator("text='K-에듀파인'").first
                if await loc.count() == 0:
                    continue
                async with page.context.expect_page(timeout=12000) as new_page_info:
                    await loc.click()
                new_page = await new_page_info.value
                await new_page.wait_for_load_state()
                return new_page
            except Exception:
                return None
    return None


async def is_settlement_screen(page: Page) -> bool:
    date_input = page.locator(
        '[id$="form.divWork.form.divSearch.form.calRecptDteFrom.calendaredit:input"]'
    ).first
    if await date_input.count() > 0:
        return True

    body = await page.locator("body").inner_text(timeout=5000)
    return "개산급정산등록" in body and "* 사용일자" in body


async def navigate(page: Page, start_date: str) -> None:
    await page.bring_to_front()
    if "install.html" in page.url:
        try:
            button = page.locator("button.mian_btn").first
            if await button.count() > 0:
                await button.click(timeout=5000)
                await page.wait_for_timeout(5000)
        except Exception:
            pass

    if "install.html" in page.url:
        query = parse_qs(urlparse(page.url).query)
        target = query.get("url", ["https://klef.gbe.kr/keris_ui/main.do"])[0]
        await page.goto(target, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(5000)

    await close_notice_popups(page)
    await switch_to_school_accounting(page)
    await close_notice_popups(page)

    if not await is_settlement_screen(page):
        for label in ["사업담당", "품의/정산", "개산급정산등록"]:
            if not await click_left_menu_row(page, label):
                print(f"[WARN] Could not click '{label}'. If needed, open it manually.")
                break

    await page.wait_for_timeout(1500)
    await set_search_date_and_query(page, start_date)


async def select_first_advance_row(page: Page) -> bool:
    row = page.locator('[id$="form.divWork.form.grdMain.body.gridrow_0"]').first
    if await row.count() == 0:
        return False
    await click_locator_dispatch(row)
    await page.wait_for_timeout(1000)
    return True


async def add_row_with_keyboard(page: Page, row: dict[str, str]) -> None:
    add_button = page.locator('[id$="form.divWork.form.divAuth3.form.btnAddRow"]').first
    if not await click_locator_dispatch(add_button) and not await visible_click(page, "행추가", timeout=4000):
        print("[WARN] 행추가 button was not found. Click the settlement grid row manually if needed.")
    await page.wait_for_timeout(700)

    first_cell = page.locator('[id$="form.divWork.form.grdDetail.body.gridrow_0.cell_0_2"]').first
    if await first_cell.count() > 0:
        await click_locator_dispatch(first_cell)
        await page.wait_for_timeout(300)

    for value in [row["date"], row["vendor"], row["amount"]]:
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(100)
        await page.keyboard.insert_text(value)
        await page.keyboard.press("Enter")
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(150)

    if not await select_evidence_type(page, row["evidence_type"]):
        print(f"[WARN] Could not select 증빙구분 '{row['evidence_type']}'.")
    await page.keyboard.press("Tab")
    await page.wait_for_timeout(150)

    await page.keyboard.press("Enter")
    await page.wait_for_timeout(100)
    await page.keyboard.insert_text(row["usage"])
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(150)


async def select_evidence_type(page: Page, evidence_type: str) -> bool:
    combo_cell = page.locator('[id$="form.divWork.form.grdDetail.body.gridrow_0.cell_0_5"]').first
    if await combo_cell.count() == 0:
        return False
    await click_locator_dispatch(combo_cell)
    await page.wait_for_timeout(200)

    drop = page.locator('[id$="form.divWork.form.grdDetail.body.gridrow_0.cell_0_5.cellcombo.dropbutton"]').first
    if await drop.count() == 0:
        drop = page.locator('[id$="form.divWork.form.grdDetail.body.gridrow_0.cell_0_5.cellcombo2.dropbutton"]').first
    if await drop.count() == 0:
        drop = page.locator('[id$="form.divWork.form.grdDetail.body.gridrow_0.cell_0_5.cellcombo3.dropbutton"]').first
    if not await click_locator_dispatch(drop):
        return False
    await page.wait_for_timeout(500)

    items = await page.locator('[id*="grdDetail.body.gridrow_0.cell_0_5"][id*="combolist.item_"]').all()
    for item in items:
        try:
            text = (await item.inner_text(timeout=500)).strip()
            box = await item.bounding_box(timeout=500)
            if evidence_type in text and box and box["x"] >= 0 and box["y"] >= 0:
                await item.click(force=True, timeout=2000)
                await page.wait_for_timeout(300)
                return True
        except Exception:
            continue
    return False


async def run(
    rows: list[dict[str, str]],
    start_date: str,
    dry_run: bool,
    cdp_url: str,
    navigate_only: bool,
    assume_first_row: bool,
) -> None:
    if rows:
        print("Preview rows:")
        for idx, row in enumerate(rows, 1):
            print(f"{idx}. {row['date']} | {row['vendor']} | {row['amount']} | {row['evidence_type']} | {row['usage']}")
    elif not navigate_only:
        raise ValueError("No rows found.")
    if dry_run:
        return

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(cdp_url)
        except Exception as exc:
            raise RuntimeError(
                "Could not connect to Chrome remote debugging. "
                "Run scripts/launch_edufine_chrome.bat, log in to 업무포털/NEIS, "
                "open K-에듀파인, then retry. "
                f"CDP URL: {cdp_url}"
            ) from exc
        page = await find_edufine_page(browser)
        if page is None:
            page = await open_edufine_from_portal(browser)
        if page is None:
            pages = await page_summary(browser)
            raise RuntimeError(
                "No K-에듀파인 page found. In the remote-debugging Chrome, log in to 업무포털/NEIS "
                "and open K-에듀파인 first.\nOpen pages:\n" + pages
            )
        await navigate(page, start_date)
        if navigate_only:
            print("Navigation check complete. No settlement rows were entered.")
            return
        if assume_first_row:
            if not await select_first_advance_row(page):
                raise RuntimeError("Could not select the first 개산급 row.")
        else:
            print("Select the relevant 개산급 row if the script cannot infer it, then press Enter here.")
            input()
        for row in rows:
            await add_row_with_keyboard(page, row)
        print("Rows entered. Confirm the grid visually before saving or submitting.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Assist K-에듀파인 개산급정산등록 row entry.")
    parser.add_argument("rows", type=Path, nargs="?", help="JSON or CSV rows")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--cdp-url", default=DEFAULT_CDP_URL)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--navigate-only", action="store_true", help="Connect and navigate without entering rows.")
    parser.add_argument("--assume-first-row", action="store_true", help="Select the first queried 개산급 row without prompting.")
    args = parser.parse_args()

    if args.rows:
        rows = [normalize(row) for row in load_rows(args.rows)]
    else:
        rows = []
    try:
        asyncio.run(run(rows, args.start_date, args.dry_run, args.cdp_url, args.navigate_only, args.assume_first_row))
    except RuntimeError as exc:
        print(f"[오류] {exc}")
        raise SystemExit(1) from None
    except Exception as exc:
        print(f"[오류] {type(exc).__name__}: {exc}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
