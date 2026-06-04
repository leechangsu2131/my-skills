"""
daangn_app.py
─────────────
당근 앱 Page Object — 실제 앱을 자동 조작하는 고수준 인터페이스.

사용법:
    driver = create_driver()
    app = DaangnApp(driver, config)
    products = app.search_and_collect("레고 스파이크")
"""

from __future__ import annotations

import time
import random
from typing import Optional

from appium.webdriver import Remote as AppiumDriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

from .models import Product, parse_price


class DaangnApp:
    """
    당근 앱 자동화 Page Object.

    Appium Inspector로 확인한 UI 요소 기반.
    앱 업데이트로 요소가 변경되면 아래 LOCATOR 상수를 수정하면 된다.
    """

    # ──────────────────────────────────────────────
    # UI 요소 로케이터 (Appium Inspector로 확인 후 업데이트)
    # 당근 앱 버전에 따라 변경될 수 있음
    # ──────────────────────────────────────────────

    # 하단 탭
    LOC_TAB_HOME = (AppiumBy.ACCESSIBILITY_ID, "홈")
    LOC_TAB_SEARCH = (AppiumBy.ACCESSIBILITY_ID, "검색")

    # 검색 화면
    LOC_SEARCH_INPUT = (AppiumBy.CLASS_NAME, "android.widget.EditText")
    LOC_SEARCH_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "검색")

    # 검색 결과 — 중고거래 탭
    LOC_FLEAMARKET_TAB = (AppiumBy.XPATH, "//*[contains(@text, '중고거래')]")

    # 상품 목록 아이템 (리사이클러뷰 내 아이템)
    LOC_PRODUCT_ITEM = (
        AppiumBy.XPATH,
        "//android.view.ViewGroup[.//android.widget.TextView]"
    )

    # 상품 내부 요소들
    LOC_TITLE = (AppiumBy.XPATH, ".//android.widget.TextView[1]")
    LOC_PRICE = (AppiumBy.XPATH, ".//android.widget.TextView[contains(@text, '원') or contains(@text, '나눔') or contains(@text, '만')]")
    LOC_LOCATION_TIME = (AppiumBy.XPATH, ".//android.widget.TextView[contains(@text, '·')]")

    # 판매완료 / 예약중 뱃지
    LOC_STATUS_BADGE = (AppiumBy.XPATH, ".//android.widget.TextView[contains(@text, '판매완료') or contains(@text, '예약중')]")

    # 뒤로가기
    LOC_BACK_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "뒤로")

    def __init__(self, driver: AppiumDriver, config: dict):
        self.driver = driver
        self.config = config
        self.wait = WebDriverWait(driver, 15)
        self.short_wait = WebDriverWait(driver, 5)

        coll_cfg = config.get("collection", {})
        self.max_scroll = coll_cfg.get("max_scroll_count", 5)
        self.scroll_pause = coll_cfg.get("scroll_pause_sec", 2.0)
        self.action_delay = coll_cfg.get("action_delay_sec", 1.5)
        self.exclude_sold = coll_cfg.get("exclude_sold", True)
        self.exclude_kw = coll_cfg.get("exclude_keywords", [])

    # ──────────────────────────────────────────────
    # 고수준 API
    # ──────────────────────────────────────────────

    def search_and_collect(self, keyword: str) -> list[Product]:
        """
        키워드로 검색하고 매물 목록을 수집한다.

        1. 검색 화면 이동
        2. 키워드 입력 및 검색
        3. 중고거래 탭 선택
        4. 스크롤하며 상품 추출
        5. 필터링 후 반환
        """
        print(f"\n{'='*50}")
        print(f"🔍 검색 시작: [{keyword}]")
        print(f"{'='*50}")

        self._go_to_search()
        self._type_and_search(keyword)
        self._select_fleamarket_tab()

        products = self._scroll_and_extract(keyword)

        # 필터링
        products = self._filter_products(products)

        print(f"✅ [{keyword}] 수집 완료: {len(products)}건")
        return products

    # ──────────────────────────────────────────────
    # 네비게이션
    # ──────────────────────────────────────────────

    def _go_to_search(self) -> None:
        """검색 탭으로 이동한다."""
        print("  📱 검색 화면으로 이동...")
        try:
            # 하단 검색 탭 클릭
            search_tab = self.wait.until(
                EC.element_to_be_clickable(self.LOC_TAB_SEARCH)
            )
            search_tab.click()
            self._delay()
        except TimeoutException:
            # 이미 검색 화면이거나 다른 상태 — 홈으로 갔다가 재시도
            print("  ⚠️ 검색 탭을 찾을 수 없음 — 홈으로 이동 후 재시도")
            try:
                home = self.wait.until(
                    EC.element_to_be_clickable(self.LOC_TAB_HOME)
                )
                home.click()
                self._delay()
                search_tab = self.wait.until(
                    EC.element_to_be_clickable(self.LOC_TAB_SEARCH)
                )
                search_tab.click()
                self._delay()
            except TimeoutException:
                print("  ❌ 검색 화면 이동 실패")

    def _type_and_search(self, keyword: str) -> None:
        """검색어를 입력하고 검색을 실행한다."""
        print(f"  ⌨️ 검색어 입력: {keyword}")

        try:
            # 검색 입력창 찾기
            search_input = self.wait.until(
                EC.element_to_be_clickable(self.LOC_SEARCH_INPUT)
            )
            search_input.click()
            self._delay(0.5)

            # 기존 텍스트 지우기
            search_input.clear()
            self._delay(0.3)

            # 키워드 입력
            search_input.send_keys(keyword)
            self._delay(0.5)

            # 엔터키로 검색 실행
            self.driver.press_keycode(66)  # KEYCODE_ENTER
            self._delay()

            print("  ✅ 검색 실행 완료")
        except TimeoutException:
            print("  ❌ 검색 입력창을 찾을 수 없음")

    def _select_fleamarket_tab(self) -> None:
        """중고거래 탭을 선택한다."""
        print("  📋 중고거래 탭 선택...")
        try:
            tab = self.short_wait.until(
                EC.element_to_be_clickable(self.LOC_FLEAMARKET_TAB)
            )
            tab.click()
            self._delay()
            print("  ✅ 중고거래 탭 선택 완료")
        except TimeoutException:
            # 이미 중고거래 탭이 선택되어 있거나 탭이 없을 수 있음
            print("  ℹ️ 중고거래 탭 별도 선택 불필요 (기본 선택됨)")

    def _go_back(self) -> None:
        """이전 화면으로 돌아간다."""
        try:
            back = self.short_wait.until(
                EC.element_to_be_clickable(self.LOC_BACK_BUTTON)
            )
            back.click()
        except TimeoutException:
            self.driver.back()
        self._delay()

    # ──────────────────────────────────────────────
    # 스크롤 & 추출
    # ──────────────────────────────────────────────

    def _scroll_and_extract(self, keyword: str) -> list[Product]:
        """
        화면을 스크롤하며 상품 정보를 추출한다.
        중복 방지를 위해 이미 수집한 제목을 추적한다.
        """
        all_products: list[Product] = []
        seen_titles: set[str] = set()

        for scroll_idx in range(self.max_scroll + 1):  # +1: 첫 화면
            if scroll_idx > 0:
                print(f"  📜 스크롤 {scroll_idx}/{self.max_scroll}...")
                self._scroll_down()

            # 현재 화면의 상품 추출
            items = self._extract_visible_items(keyword)

            new_count = 0
            for item in items:
                if item.title not in seen_titles:
                    seen_titles.add(item.title)
                    all_products.append(item)
                    new_count += 1

            print(f"  📦 현재 화면: {len(items)}건 발견, 신규 {new_count}건")

            # 새 상품이 없으면 더 이상 스크롤 불필요
            if new_count == 0 and scroll_idx > 0:
                print("  ℹ️ 새 상품 없음 — 스크롤 중단")
                break

        return all_products

    def _extract_visible_items(self, keyword: str) -> list[Product]:
        """현재 화면에 보이는 상품들을 추출한다."""
        products = []

        try:
            # 화면의 모든 텍스트 뷰를 가져와서 패턴으로 상품 정보 추출
            text_views = self.driver.find_elements(
                AppiumBy.CLASS_NAME, "android.widget.TextView"
            )

            texts = []
            for tv in text_views:
                try:
                    t = tv.text
                    if t:
                        texts.append(t)
                except StaleElementReferenceException:
                    continue

            # 텍스트들에서 상품 정보 패턴 매칭
            products = self._parse_product_texts(texts, keyword)

        except Exception as e:
            print(f"  ⚠️ 요소 추출 중 오류: {e}")

        return products

    def _parse_product_texts(
        self, texts: list[str], keyword: str
    ) -> list[Product]:
        """
        화면에서 수집한 텍스트 목록을 분석하여 상품 목록으로 변환한다.

        당근 앱의 상품 목록은 대체로 이런 순서로 텍스트가 나열됨:
          - 제목
          - 지역 · 시간
          - 가격

        이 패턴을 인식하여 Product 객체로 변환한다.
        """
        products = []
        i = 0

        while i < len(texts):
            text = texts[i]

            # 가격 패턴이 보이면 그 위에 제목/지역이 있을 수 있음
            if self._looks_like_price(text):
                product = self._try_build_product(texts, i, keyword)
                if product:
                    products.append(product)
            i += 1

        return products

    def _try_build_product(
        self, texts: list[str], price_idx: int, keyword: str
    ) -> Optional[Product]:
        """
        가격 텍스트 위치를 기준으로 주변 텍스트에서 상품 정보를 조합한다.
        """
        price_text = texts[price_idx]

        # 가격 위에 지역·시간, 그 위에 제목이 있는 패턴
        title = ""
        location = ""
        time_text = ""
        status = "판매중"

        # 가격 바로 위 텍스트들을 역순으로 확인
        for offset in range(1, min(4, price_idx + 1)):
            candidate = texts[price_idx - offset]

            if "·" in candidate and not title:
                # "부산진구 · 3시간 전" 패턴
                parts = candidate.split("·")
                location = parts[0].strip()
                time_text = parts[1].strip() if len(parts) > 1 else ""
            elif candidate in ("판매완료", "예약중"):
                status = candidate
            elif not title and not self._looks_like_price(candidate):
                # 나머지 중 첫 번째 → 제목으로 추정
                if len(candidate) > 2 and candidate not in ("중고거래", "동네생활", "알바", "부동산"):
                    title = candidate

        if not title:
            return None

        return Product(
            title=title,
            price=parse_price(price_text),
            price_text=price_text,
            location=location,
            time_text=time_text,
            keyword=keyword,
            status=status,
        )

    # ──────────────────────────────────────────────
    # 스크롤
    # ──────────────────────────────────────────────

    def _scroll_down(self) -> None:
        """화면을 아래로 스크롤한다."""
        size = self.driver.get_window_size()
        start_x = size["width"] // 2
        start_y = int(size["height"] * 0.75)
        end_y = int(size["height"] * 0.25)

        self.driver.swipe(start_x, start_y, start_x, end_y, duration=800)
        time.sleep(self.scroll_pause)

    # ──────────────────────────────────────────────
    # 필터링
    # ──────────────────────────────────────────────

    def _filter_products(self, products: list[Product]) -> list[Product]:
        """불필요한 매물을 필터링한다."""
        filtered = []
        for p in products:
            # 판매완료 제외
            if self.exclude_sold and p.status == "판매완료":
                continue
            # 제외 키워드 확인
            if any(kw in p.title for kw in self.exclude_kw):
                continue
            filtered.append(p)

        removed = len(products) - len(filtered)
        if removed > 0:
            print(f"  🔽 필터링: {removed}건 제외")

        return filtered

    # ──────────────────────────────────────────────
    # 헬퍼
    # ──────────────────────────────────────────────

    @staticmethod
    def _looks_like_price(text: str) -> bool:
        """텍스트가 가격처럼 보이는지 판단한다."""
        if not text:
            return False
        indicators = ["원", "만원", "나눔", "무료", "가격미정"]
        if any(ind in text for ind in indicators):
            return True
        # 순수 숫자 (콤마 포함)
        cleaned = text.replace(",", "").replace(" ", "")
        return cleaned.isdigit() and len(cleaned) >= 3

    def _delay(self, seconds: float | None = None) -> None:
        """사람처럼 보이게 랜덤 딜레이를 준다."""
        if seconds:
            time.sleep(seconds)
        else:
            jitter = random.uniform(0.8, 1.5)
            time.sleep(self.action_delay * jitter)
