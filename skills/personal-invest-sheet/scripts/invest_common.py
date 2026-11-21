"""투자 스크립트 공통 설정 (공개 저장소용: 종목·명의·결과물은 코드에 두지 않는다).

공용 .env (OneDrive "96. 인증/.env") 에서 읽는 값 — 이 스킬 전용 키는 PERSONAL_INVEST_SHEET__ 접두사:
    PERSONAL_INVEST_SHEET__INVEST_DIR    드라이브 invest 폴더 (문서·universe.csv 가 있는 곳, 비공개)
    PERSONAL_INVEST_SHEET__UNIVERSE      종목 목록 CSV (기본: <INVEST_DIR>/portfolio/universe.csv)
    PERSONAL_INVEST_SHEET__OUTPUT_DIR    결과물 폴더 (기본: 내 문서/my-skills-data/personal-invest-sheet)
    PERSONAL_INVEST_SHEET__KIWOOM_TAG    매매근거 칸 앞 태그 (기본: [키움])
    KIWOOM_APPKEY / KIWOOM_SECRETKEY / DART_API_KEY / NAVER_CLIENT_ID / NAVER_CLIENT_SECRET

universe.csv 열: role(holding/watch/closed/benchmark/fx), group, code, name, yahoo_ticker, currency,
                 asset(stock/etf/other), fin(Y=금융·지주) ...
"""
from __future__ import annotations

import csv
import os
import pathlib
import sys

sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents
                            if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir, load_env  # noqa: E402

SKILL = "personal-invest-sheet"
load_env(skill=SKILL)

# 결과물 하위 폴더 (드라이브 invest/data 를 OUTPUT_DIR 로 쓰던 이름과 같게)
SUBDIRS = {"kiwoom": "invest-output", "sentiment": "sentiment_out", "portfolio": "portfolio_out",
           "finance": "finance", "cache": "cache"}


def invest_dir() -> pathlib.Path | None:
    p = os.environ.get("INVEST_DIR")
    return pathlib.Path(p) if p and os.path.isdir(p) else None


def universe_path() -> pathlib.Path:
    p = os.environ.get("UNIVERSE")
    if p:
        return pathlib.Path(p)
    d = invest_dir()
    if d is None:
        sys.exit("종목 목록을 못 찾았습니다. 공용 .env 에 PERSONAL_INVEST_SHEET__INVEST_DIR 또는 __UNIVERSE 를 넣어 주세요.")
    return d / "portfolio" / "universe.csv"


def out_dir(kind: str) -> pathlib.Path:
    """결과물 폴더. OUTPUT_DIR/<하위폴더>, 없으면 내 문서/my-skills-data/personal-invest-sheet/<하위폴더>."""
    base = os.environ.get("OUTPUT_DIR")
    root = pathlib.Path(os.path.expandvars(base)) if base else data_dir(SKILL)
    p = root / SUBDIRS.get(kind, kind)
    p.mkdir(parents=True, exist_ok=True)
    return p


def universe_rows() -> list[dict]:
    with open(universe_path(), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def stocks(currency: str, roles=("holding", "watch"), include_closed: bool = False) -> list[dict]:
    """개별 주식만 (asset=stock). currency 는 'USD' 또는 'KRW'.
    반환: [{code, name, yahoo, role, fin(bool)}]  — 수집 스크립트가 종목을 코드에 박지 않도록 여기서 읽는다."""
    roles = set(roles) | ({"closed"} if include_closed else set())
    out = []
    for r in universe_rows():
        if r.get("asset") != "stock" or r.get("currency") != currency or r.get("role") not in roles:
            continue
        out.append({"code": r["code"], "name": r.get("name", ""), "yahoo": r.get("yahoo_ticker") or r["code"],
                    "role": r["role"], "fin": r.get("fin", "").upper() == "Y"})
    if not out:
        sys.exit(f"universe.csv 에 {currency} 개별 주식({', '.join(sorted(roles))})이 없습니다.")
    return out


def role_label(role: str) -> str:
    return {"holding": "보유", "watch": "관심", "closed": "정리"}.get(role, role)


def kiwoom_tag() -> str:
    return os.environ.get("KIWOOM_TAG", "[키움]")
