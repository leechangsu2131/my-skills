"""
후지필름 Apeos C2561 용지 트레이 진단

복합기 웹 API(인증 없이 조회 가능)로 각 트레이 등록 상태를 읽고,
일반 PC 인쇄(흰색 일반용지 A4)와 맞지 않는 설정이 있는지 표시합니다.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

COPIER_IP = os.getenv("COPIER_IP", "10.21.136.237")
API = f"http://{COPIER_IP}/home/api/paper-tray"

SIZE_KO = {
    "A4": "A4",
    "A3": "A3",
    "UNKNOWN": "미설정",
}
TYPE_KO = {
    "stationary": "일반 용지",
    "recycled": "재생 용지",
    "fineQuality": "고급 용지",
}
COLOR_KO = {
    "WHITE": "흰색",
    "GRAY": "회색",
    "BLUE": "파랑",
    "YELLOW": "노랑",
    "GREEN": "초록",
    "PINK": "분홍",
}


def fetch_trays() -> dict:
    with urllib.request.urlopen(API, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    print(f"복합기: {COPIER_IP}")
    print(f"API: {API}")
    print()

    try:
        data = fetch_trays()
    except Exception as e:
        print(f"복합기 API 접속 실패: {e}")
        print("학교 네트워크에 연결된 PC에서 다시 실행하세요.")
        return 1

    trays = data.get("PaperTrays", [])
    if not trays:
        print("트레이 정보가 없습니다.")
        return 1

    problem = False
    for t in trays:
        if t.get("LogicalTrayType") != "TRAY":
            continue
        num = t.get("LogicalNum")
        size = t.get("MediumSize", "?")
        ptype = t.get("MediumType", "?")
        color = t.get("Color", "?")
        remain = t.get("Remaining", "?")
        auto = t.get("AutoTraySelect")
        pri = t.get("Priority")

        print(f"[트레이 {num}]")
        print(f"  등록 용지: {SIZE_KO.get(size, size)} / {TYPE_KO.get(ptype, ptype)} / {COLOR_KO.get(color, color)}")
        print(f"  잔량: {remain}%  |  자동트레이선택: {auto}  |  우선순위: {pri}")

        if num == 1 and size == "A4" and (ptype != "stationary" or color != "WHITE"):
            problem = True
            print("  >>> 문제: 트레이1이 A4이지만 '일반 용지·흰색'이 아닙니다.")
            print("      Windows/한글의 평범한 인쇄는 보통 '일반 용지 흰색 A4'를 요청합니다.")
            print("      복합기가 트레이1을 건너뛰고, A4가 들어 있는 다른 트레이만 찾을 수 있습니다.")
        print()

    print("=" * 60)
    if problem:
        print("진단 결과: 복합기 트레이1 용지 종류/색상이 일반 인쇄와 불일치합니다.")
        print()
        print("복합기 패널에서 수정 (기계 관리자 비밀번호 11111):")
        print("  홈 → 설정(톱니) → [용지 트레이 설정] → [트레이 1]")
        print("    용지 크기: A4")
        print("    용지 종류: 일반 용지  (재생 용지 X)")
        print("    용지 색상: 흰색      (회색 X)")
        print("  트레이 2는 실제 용지에 맞게 A3 / 일반 용지 / 흰색 유지")
    else:
        print("진단 결과: 트레이 등록은 정상으로 보입니다.")
        print("그래도 인쇄가 안 되면 Windows 프린터 속성의 용지함도 확인하세요.")
    return 0 if not problem else 2


if __name__ == "__main__":
    raise SystemExit(main())
