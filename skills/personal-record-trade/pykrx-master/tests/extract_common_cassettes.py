#!/usr/bin/env python
"""
개별 테스트 cassette에서 공통 ticker 초기화 요청을 추출하여
common cassette으로 분리하는 스크립트

공통 cassette:
- etx_ticker_init.yaml: EtxTicker 초기화 (ETF/ETN/ELW ticker 목록)
- stock_ticker_init.yaml: StockTicker 초기화 (KOSPI/KOSDAQ/KONEX ticker 목록)

실행 후:
1. 각 테스트 cassette에서 공통 요청 제거
2. 파일 크기 대폭 감소 (119MB → 예상 20-30MB)
"""

import urllib.parse
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
CASSETTES_DIR = PROJECT_ROOT / "tests" / "cassettes"
COMMON_DIR = CASSETTES_DIR / "common"

# 날짜 파라미터 키
DATE_KEYS = {
    "strtDd",
    "endDd",
    "trdDd",
    "fromdate",
    "todate",
    "startDt",
    "endDt",
    "stDt",
    "enDt",
    "date",
}

# BLD 코드 그룹 (날짜 파라미터가 없는 경우만 공통화)
ETX_TICKER_BLDS = {
    "dbms/MDC/STAT/standard/MDCSTAT04601",  # ETF ticker
    "dbms/MDC/STAT/standard/MDCSTAT04801",  # ETN ticker
    "dbms/MDC/STAT/standard/MDCSTAT04301",  # ELW ticker
}

STOCK_TICKER_BLDS = {
    "dbms/MDC/STAT/standard/MDCSTAT01901",  # 전체 ticker (KOSPI/KOSDAQ/KONEX)
}

FINDER_BLDS = {
    "dbms/comm/finder/finder_stkisu",  # 종목 기본정보
    "dbms/comm/finder/finder_listdelisu",  # 상장폐지 종목
}

INDEX_KIND_BLDS = {
    "dbms/MDC/STAT/standard/MDCSTAT06701",  # 지수 구성종목
    "dbms/MDC/STAT/standard/MDCSTAT08501",  # 업종/섹터 구성종목
}


def normalize_body(body) -> str:
    """Body를 문자열로 변환하고 URL decode."""
    if body is None:
        return ""
    if isinstance(body, dict):
        body = body.get("string", "")
    if isinstance(body, bytes):
        body = body.decode()
    if not isinstance(body, str):
        return ""
    return urllib.parse.unquote(body)


def extract_bld_from_body(body: str) -> str:
    """POST body에서 bld 파라미터 추출 (URL-decoded)"""
    if not body:
        return ""
    for param in body.split("&"):
        if param.startswith("bld="):
            return param.split("=", 1)[1]
    return ""


def has_date_param(body: str) -> bool:
    """Body 안에 날짜 관련 파라미터가 있는지 검사"""
    for param in body.split("&"):
        key = param.split("=", 1)[0]
        if key in DATE_KEYS:
            return True
    return False


def categorize_interactions(cassette_data: dict) -> dict:
    """Cassette의 interactions를 카테고리별로 분류"""
    categories = {
        "etx_ticker": [],
        "stock_ticker": [],
        "finder": [],
        "index_kind": [],
        "test_specific": [],
    }

    for interaction in cassette_data.get("interactions", []):
        request = interaction.get("request", {})
        body_str = normalize_body(request.get("body", {}))

        bld = extract_bld_from_body(body_str)
        if not bld:
            categories["test_specific"].append(interaction)
            continue

        # 날짜 파라미터가 있는 요청은 공통화하지 않음
        if has_date_param(body_str):
            categories["test_specific"].append(interaction)
            continue

        if bld in ETX_TICKER_BLDS:
            categories["etx_ticker"].append(interaction)
        elif bld in STOCK_TICKER_BLDS:
            categories["stock_ticker"].append(interaction)
        elif bld in FINDER_BLDS:
            categories["finder"].append(interaction)
        elif bld in INDEX_KIND_BLDS:
            categories["index_kind"].append(interaction)
        else:
            categories["test_specific"].append(interaction)

    return categories


def merge_common_interactions(existing: list, new: list) -> list:
    """공통 interaction 병합 (중복 제거)"""
    # 요청 시그니처로 중복 체크
    seen = set()
    merged = []

    for interaction in existing + new:
        request = interaction.get("request", {})
        uri = request.get("uri", {})
        body_str = normalize_body(request.get("body", {}))

        bld = extract_bld_from_body(body_str)
        signature = (uri, bld)

        if signature not in seen:
            seen.add(signature)
            merged.append(interaction)

    return merged


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="날짜 파라미터가 없는 공통 호출을 cassette에서 추출해 공유 cassette으로 분리합니다.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제로 파일을 수정하지 않고 결과만 출력",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("📦 공통 Cassette 추출 시작")
    print("=" * 70)

    # 공통 cassette 초기화
    common_cassettes = {
        "etx_ticker": {"version": 1, "interactions": []},
        "stock_ticker": {"version": 1, "interactions": []},
        "finder": {"version": 1, "interactions": []},
        "index_kind": {"version": 1, "interactions": []},
    }

    cassette_files = list(CASSETTES_DIR.glob("Test*.yaml"))
    print(f"\n📋 {len(cassette_files)}개 cassette 파일 분석 중...\n")

    modified_count = 0
    total_removed = 0

    for cassette_path in cassette_files:
        try:
            with open(cassette_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data or "interactions" not in data:
                continue

            original_count = len(data["interactions"])

            # Interaction 분류
            categories = categorize_interactions(data)

            # 공통 cassette에 추가
            for key in ("etx_ticker", "stock_ticker", "finder", "index_kind"):
                common_cassettes[key]["interactions"] = merge_common_interactions(
                    common_cassettes[key]["interactions"],
                    categories[key],
                )

            # 테스트 고유 요청만 남김
            removed = original_count - len(categories["test_specific"])
            if removed > 0:
                if not args.dry_run:
                    data["interactions"] = categories["test_specific"]
                    with open(cassette_path, "w", encoding="utf-8") as f:
                        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

                print(
                    f"  {'[DRY RUN] ' if args.dry_run else ''}✂️  {cassette_path.name}"
                )
                print(
                    f"     {original_count} → {len(categories['test_specific'])} interactions (-{removed})"
                )
                modified_count += 1
                total_removed += removed

        except Exception as e:
            print(f"  ❌ 오류: {cassette_path.name} - {e}")

    # 공통 cassette 저장
    print("\n💾 공통 Cassette 저장 중...")

    if not args.dry_run:
        COMMON_DIR.mkdir(exist_ok=True)

    for name, data in common_cassettes.items():
        if data["interactions"]:
            cassette_path = COMMON_DIR / f"{name}_init.yaml"

            if not args.dry_run:
                with open(cassette_path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

            print(
                f"  {'[DRY RUN] ' if args.dry_run else ''}✅ {cassette_path.name} ({len(data['interactions'])} interactions)"
            )

    # 결과 요약
    print("\n" + "=" * 70)
    print(f"✨ {modified_count}개 파일 수정")
    print(f"🗑️  총 {total_removed}개 중복 interaction 제거")

    if args.dry_run:
        print("\n⚠️  DRY RUN 모드: 실제 파일이 수정되지 않았습니다.")
        print("   실제로 적용하려면 --dry-run 없이 실행하세요.")
    else:
        print(f"\n📂 공통 cassette 위치: {COMMON_DIR}")
        print("   각 테스트는 이제 공통 cassette을 자동으로 참조합니다.")

    print("=" * 70)


if __name__ == "__main__":
    main()
