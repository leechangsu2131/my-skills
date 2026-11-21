#!/usr/bin/env python3
"""한국 종목 재무 수집 (DART 오픈API + yfinance 시총) -> fundamentals_kr.csv

준비
  1) DART 인증키 발급 (무료): https://opendart.fss.or.kr  -> 인증키 신청
  2) 키는 코드나 대화에 적지 말고 환경변수 DART_API_KEY 로만 둔다
       Windows PowerShell(이 창에서만): $env:DART_API_KEY="발급받은키"
       Windows(계속 유지)             : setx DART_API_KEY "발급받은키"   (새 터미널부터 적용)
       Mac/Linux                      : export DART_API_KEY="발급받은키"
       또는 my-skills 공용 .env (OneDrive '96. 인증' 폴더) 에 한 줄을 추가한다 (스크립트·드라이브 폴더에는 .env를 두지 말 것)
                       DART_API_KEY=발급받은키
  3) pip install requests pandas yfinance

사용법
  python fetch_fundamentals_kr.py            # universe.csv 의 한국 개별주(보유·관심) 전체
  python fetch_fundamentals_kr.py 005930     # 일부만 (처음엔 이렇게 시험)

출력 (같은 폴더)
  fundamentals_kr.csv   전체 항목 (*_eok 열은 억원)
  sheet_paste_kr.csv    시트 '📥 재무수집' 탭 A:Q 열 순서 그대로 (붙여넣기용)
  dart_corp_codes.json  종목코드 -> DART 고유번호 캐시 (지워도 됨, 다시 받음)

계산식 (미국 스크립트와 같은 정의)
  FCF      = 영업활동현금흐름 - 유형자산의 취득        (최근 4분기 합 = TTM)
  순부채   = 차입금(단기·장기차입금, 사채, 리스부채) - 현금성자산(현금 + 단기금융상품)
  투자자본 = 자본총계 + 차입금   (야후 Invested Capital과 비슷한 정의)
  ROIC     = 영업이익 x (1-21%) / 투자자본
  TTM      = 직전 사업연도 + 올해 누적 - 작년 같은 기간 누적 (최신 보고서가 사업보고서면 그대로)

주의
  - 처음 돌려 보는 코드라 계정명이 회사마다 달라 못 찾는 항목이 있을 수 있다. warn 열을 꼭 본다.
  - 금융업(현대해상)은 FCF·순부채가 의미 없어 참고만 한다.
  - 시총·PER·PBR은 DART에 없어 yfinance(.KS/.KQ)에서 가져온다. 못 가져오면 비워 둔다.
"""
import datetime as dt
import io
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd
import requests

try:
    import yfinance as yf
except ImportError:  # 시총·PER·PBR 없이도 재무는 수집된다
    yf = None

API = "https://opendart.fss.or.kr/api"
EOK = 1e8
from invest_common import out_dir, role_label, stocks  # noqa: E402  (공용 .env 도 여기서 읽음)

CORP_CACHE = str(out_dir("cache") / "dart_corp_codes.json")
TAX = 0.21
NAN = float("nan")


def _suffix(yahoo):
    return "." + yahoo.rsplit(".", 1)[-1] if "." in yahoo else ".KS"


# 종목코드: (이름, 구분, 야후 접미사) -- universe.csv(비공개)의 한국 개별 주식(ETF는 재무제표가 없어 제외).
# 기본 수집은 보유·관심. 정리(closed) 종목은 코드를 인자로 직접 줄 때만.
_KR_ALL = stocks("KRW", include_closed=True)
KR = {s["code"]: (s["name"], role_label(s["role"]), _suffix(s["yahoo"])) for s in _KR_ALL}
KR_DEFAULT = [s["code"] for s in _KR_ALL if s["role"] != "closed"]
FINANCIALS = {s["code"] for s in _KR_ALL if s["fin"]}

# 계정 식별: (account_id 후보, 계정명 후보). 계정명은 공백을 뺀 뒤 정확히 일치해야 한다.
OCF = (("ifrs-full_CashFlowsFromUsedInOperatingActivities",),
       ("영업활동현금흐름", "영업활동으로인한현금흐름", "영업활동순현금흐름"))
CAPEX = (("ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",),
         ("유형자산의취득", "유형자산취득"))
OPINC = (("dart_OperatingIncomeLoss", "ifrs-full_ProfitLossFromOperatingActivities"),
         ("영업이익", "영업이익(손실)"))
REV = (("ifrs-full_Revenue",), ("매출액", "수익(매출액)", "영업수익", "매출"))
EQUITY = (("ifrs-full_Equity",), ("자본총계",))
# PER·PBR 계산용 (야후에서 못 가져왔을 때): 지배주주 기준 자본·순이익, 없으면 전체 기준
EQ_OWNERS = (("ifrs-full_EquityAttributableToOwnersOfParent",),
             ("지배기업의소유주에게귀속되는자본", "지배기업소유주지분", "지배기업의소유주지분"))
NETINC = (("ifrs-full_ProfitLossAttributableToOwnersOfParent",),
          ("지배기업의소유주에게귀속되는당기순이익", "지배기업소유주지분순이익",
           "지배기업의소유주에게귀속되는분기순이익", "지배기업의소유주에게귀속되는반기순이익"))
NETINC_ALL = (("ifrs-full_ProfitLoss",),
              ("당기순이익", "당기순이익(손실)", "분기순이익", "반기순이익", "분기순이익(손실)", "반기순이익(손실)"))
CASH = (("ifrs-full_CashAndCashEquivalents",), ("현금및현금성자산",))
EXTRA_CASH = ("단기금융상품", "단기금융자산", "단기투자자산")
DEBT_NAMES = ("단기차입금", "유동성장기부채", "유동성장기차입금", "유동성사채", "사채",
              "장기차입금", "전환사채", "교환사채", "리스부채", "유동리스부채",
              "비유동리스부채", "유동성리스부채")

_seen_msgs = set()


def load_env(path=".env"):
    """실행하는 폴더의 .env 파일(KEY=값, 한 줄에 하나)을 읽어 환경변수로 넣는다.
    이미 설정된 환경변수는 덮어쓰지 않는다."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            if k.startswith("export "):
                k = k[7:].strip()
            os.environ.setdefault(k, v.strip().strip('"').strip("'"))


def get_key():
    # 공용 .env 는 invest_common 을 불러올 때 이미 읽었다 (OS 환경변수가 있으면 그것이 우선)
    key = os.environ.get("DART_API_KEY", "").strip()
    if not key:
        sys.exit("환경변수 DART_API_KEY가 없습니다. 파일 맨 위 '준비' 2번을 따라 설정한 뒤 새 터미널에서 다시 실행하세요.")
    return key


def num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").strip()
    if s in ("", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_corp_codes(key):
    """종목코드(6자리) -> DART 고유번호(8자리). 처음 한 번만 받아 캐시한다."""
    if os.path.exists(CORP_CACHE):
        with open(CORP_CACHE, encoding="utf-8") as f:
            return json.load(f)
    r = requests.get(f"{API}/corpCode.xml", params={"crtfc_key": key}, timeout=120)
    r.raise_for_status()
    try:
        z = zipfile.ZipFile(io.BytesIO(r.content))
    except zipfile.BadZipFile:
        sys.exit("고유번호 파일을 받지 못했습니다. 키가 맞는지 확인하세요. 응답: " + r.text[:200])
    root = ET.fromstring(z.read(z.namelist()[0]))
    out = {}
    for it in root.iter("list"):
        sc = (it.findtext("stock_code") or "").strip()
        cc = (it.findtext("corp_code") or "").strip()
        if sc and cc:
            out[sc] = cc
    with open(CORP_CACHE, "w", encoding="utf-8") as f:
        json.dump(out, f)
    return out


def fetch_report(key, corp, year, rc, fs_pref=None):
    """전체 재무제표 한 건. 연결(CFS) 먼저, 없으면 별도(OFS). (fs, rows) 또는 (None, None)."""
    for fs in ([fs_pref] if fs_pref else ["CFS", "OFS"]):
        try:
            r = requests.get(
                f"{API}/fnlttSinglAcntAll.json",
                params={"crtfc_key": key, "corp_code": corp, "bsns_year": str(year),
                        "reprt_code": rc, "fs_div": fs},
                timeout=60,
            )
            j = r.json()
        except Exception as e:  # noqa: BLE001
            msg = f"{year}/{rc} 호출 실패: {type(e).__name__}"
            if msg not in _seen_msgs:
                _seen_msgs.add(msg)
                print("  " + msg)
            continue
        time.sleep(0.15)
        st = j.get("status")
        if st == "000" and j.get("list"):
            return fs, j["list"]
        if st in ("010", "011", "012", "020"):  # 키 오류·사용 제한: 더 해도 소용없다
            sys.exit(f"DART 오류 {st}: {j.get('message')}")
        if st not in ("000", "013") and (st, j.get("message")) not in _seen_msgs:
            _seen_msgs.add((st, j.get("message")))
            print(f"  DART 응답 {st}: {j.get('message')}")
    return None, None


def find(rows, sj, spec):
    ids, names = spec
    sjs = {"IS": ("IS", "CIS"), "BS": ("BS",), "CF": ("CF",)}[sj]
    cand = [r for r in rows if r.get("sj_div") in sjs]
    for i in ids:
        for r in cand:
            if r.get("account_id") == i:
                return r
    for n in names:
        for r in cand:
            if (r.get("account_nm") or "").replace(" ", "") == n:
                return r
    return None


def flow(rows, sj, spec, annual):
    """기간 값. 사업보고서는 당기 금액, 분기·반기 보고서는 올해 누적 금액."""
    r = find(rows, sj, spec)
    if r is None:
        return None
    if annual or sj == "CF":  # 현금흐름표는 분기 보고서도 이미 누적
        return num(r.get("thstrm_amount"))
    v = num(r.get("thstrm_add_amount"))  # 손익계산서 누적
    return v if v is not None else num(r.get("thstrm_amount"))  # 1분기는 누적 열이 없다


def pair(rows, sj, spec):
    """사업보고서의 (당기, 전기) 금액."""
    r = find(rows, sj, spec)
    if r is None:
        return None, None
    return num(r.get("thstrm_amount")), num(r.get("frmtrm_amount"))


def balance(rows, spec):
    r = find(rows, "BS", spec)
    return num(r.get("thstrm_amount")) if r else None


def candidates(today):
    y = today.year
    return [(y, "11014"), (y, "11012"), (y, "11013"), (y - 1, "11011"), (y - 1, "11014")]


def eok(v):
    return round(v / EOK, 2) if v is not None else NAN


def market(code, suffix):
    if yf is None:
        return {}
    alt = ".KQ" if suffix == ".KS" else ".KS"
    for suf in (suffix, alt):
        try:
            info = yf.Ticker(code + suf).info or {}
        except Exception:  # noqa: BLE001
            continue
        mc = info.get("marketCap")
        if mc:
            return {
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "market_cap": mc,
                "pb": info.get("priceToBook"),
                "pe": info.get("trailingPE"),
            }
    return {}


def collect(key, corp_codes, code, today):
    name, group, suffix = KR.get(code, (code, "", ".KS"))
    base = {"ticker": code, "group": group, "name": name, "source": "DART",
            "date": today.isoformat()}
    warn = []
    corp = corp_codes.get(code)
    if not corp:
        base["warn"] = "DART고유번호없음(상장사 아님/코드오류)"
        return base

    latest = None
    for yr, rc in candidates(today):
        fs, rows = fetch_report(key, corp, yr, rc)
        if rows:
            latest = (yr, rc, fs, rows)
            break
    if latest is None:
        base["warn"] = "재무제표없음"
        return base
    yr, rc, fs, rows = latest
    annual = rc == "11011"
    prev_annual = prev_same = None
    if not annual:
        _, prev_annual = fetch_report(key, corp, yr - 1, "11011", fs)
        _, prev_same = fetch_report(key, corp, yr - 1, rc, fs)
        if not prev_annual or not prev_same:
            warn.append("TTM불가:전기자료없음")
    label = {"11011": "사업", "11014": "3분기", "11012": "반기", "11013": "1분기"}[rc]

    def ttm(spec, sj):
        cur = flow(rows, sj, spec, annual)
        if annual:
            return cur
        if cur is None or not prev_annual or not prev_same:
            return None
        a = flow(prev_annual, sj, spec, True)
        p = flow(prev_same, sj, spec, False)
        if a is None or p is None:
            return None
        return a + cur - p

    ocf = ttm(OCF, "CF")
    capex = ttm(CAPEX, "CF")
    capex = abs(capex) if capex is not None else None
    ebit = ttm(OPINC, "IS")
    rev = ttm(REV, "IS")
    for v, lab in ((ocf, "영업CF"), (capex, "CapEx"), (ebit, "영업이익"), (rev, "매출")):
        if v is None:
            warn.append(lab + "없음")
    fcf = ocf - capex if ocf is not None and capex is not None else None

    equity = balance(rows, EQUITY)
    if equity is None:
        warn.append("자본없음")
    eq_own = balance(rows, EQ_OWNERS)
    if eq_own is None:
        eq_own = equity
    ni = ttm(NETINC, "IS")
    if ni is None:
        ni = ttm(NETINC_ALL, "IS")
    debt, seen = 0.0, set()
    debt_items = []  # 어떤 계정을 차입금으로 잡았는지 확인용
    for r in rows:
        if r.get("sj_div") != "BS":
            continue
        nm = (r.get("account_nm") or "").replace(" ", "")
        if nm in DEBT_NAMES and nm not in seen:
            v = num(r.get("thstrm_amount"))
            if v is not None:
                debt += v
                seen.add(nm)
                debt_items.append(f"{nm}:{round(v / EOK)}억")
    if not seen:
        warn.append("차입금항목없음(0으로 처리)")
    cash = balance(rows, CASH)
    extra = 0.0
    for r in rows:
        if r.get("sj_div") == "BS" and (r.get("account_nm") or "").replace(" ", "") in EXTRA_CASH:
            extra += num(r.get("thstrm_amount")) or 0.0
    cash_total = (cash or 0.0) + extra if (cash is not None or extra) else None
    if cash_total is None:
        warn.append("현금없음")
    net_debt = debt - cash_total if cash_total is not None else None
    invested = equity + debt if equity is not None else None

    roic = (ebit * (1 - TAX) / invested * 100) if ebit is not None and invested and invested > 0 else NAN
    opm = (ebit / rev * 100) if ebit is not None and rev else NAN

    # 최근 회계연도 성장률 (시트 기업분석의 매출성장률·FCF성장률과 같은 기준)
    g_rows = rows if annual else prev_annual
    rev_g = fcf_g = NAN
    if g_rows:
        r0, r1 = pair(g_rows, "IS", REV)
        if r0 is not None and r1 and r1 > 0:
            rev_g = round((r0 / r1 - 1) * 100, 1)
        o0, o1 = pair(g_rows, "CF", OCF)
        c0, c1 = pair(g_rows, "CF", CAPEX)
        if None not in (o0, o1, c0, c1):
            f0, f1 = o0 - abs(c0), o1 - abs(c1)
            if f1 > 0:
                fcf_g = round((f0 / f1 - 1) * 100, 1)

    if code in FINANCIALS:
        warn.append("금융업:순부채·FCF·ROIC 참고불가")
    m = market(code, suffix)
    if not m:
        warn.append("시총·PER·PBR 못 가져옴")
    pb, pe = m.get("pb"), m.get("pe")
    mc = m.get("market_cap")
    if mc:  # 야후에 PER·PBR이 없으면 DART 값으로 직접 계산
        if not pb and eq_own and eq_own > 0:
            pb = round(mc / eq_own, 2)
            warn.append("PBR은 시총/지배자본으로 계산")
        if not pe and ni is not None:
            if ni > 0:
                pe = round(mc / ni, 2)
                warn.append("PER은 시총/최근4분기 순이익으로 계산")
            else:
                warn.append("PER없음:순이익<=0")

    base.update({
        "report": f"{yr} {label} {fs}",
        "price_krw": m.get("price"),
        "market_cap_eok": round(m["market_cap"] / EOK, 2) if m.get("market_cap") else NAN,
        "total_debt_eok": eok(debt),
        "cash_eok": eok(cash_total),
        "net_debt_eok": eok(net_debt),
        "ocf_ttm_eok": eok(ocf),
        "capex_ttm_eok": eok(capex),
        "fcf_ttm_eok": eok(fcf),
        "ebit_ttm_eok": eok(ebit),
        "revenue_ttm_eok": eok(rev),
        "equity_eok": eok(equity),
        "invested_capital_eok": eok(invested),
        "roic_pct_21": round(roic, 2) if pd.notna(roic) else NAN,
        "op_margin_pct": round(opm, 2) if pd.notna(opm) else NAN,
        "rev_growth_fy_pct": rev_g,
        "fcf_growth_fy_pct": fcf_g,
        "net_income_ttm_eok": eok(ni),
        "pb": pb,
        "pe_trailing": pe,
        "debt_items": " | ".join(debt_items),
        "warn": ";".join(warn),
    })
    return base


def main():
    key = get_key()
    codes = sys.argv[1:] or KR_DEFAULT
    corp_codes = load_corp_codes(key)
    today = dt.date.today()
    rows = []
    for i, code in enumerate(codes, 1):
        print(f"[{i}/{len(codes)}] {code} {KR.get(code, ('',))[0]} ...", flush=True)
        try:
            rows.append(collect(key, corp_codes, code, today))
        except Exception as e:  # noqa: BLE001
            print(f"  실패: {type(e).__name__}: {e}")
            rows.append({"ticker": code, "source": "DART", "date": today.isoformat(),
                         "warn": f"실패:{type(e).__name__}"})
    df = pd.DataFrame(rows)
    df.to_csv(out_dir("finance") / "fundamentals_kr.csv", index=False, encoding="utf-8-sig")

    def col(c):
        return df[c] if c in df.columns else NAN

    def r2(c):
        return pd.to_numeric(col(c), errors="coerce").round(2)

    paste = pd.DataFrame({
        "티커": col("ticker"), "구분": col("group"), "수집일": col("date"),
        "종가": col("price_krw"), "시총": col("market_cap_eok"), "순부채": col("net_debt_eok"),
        "FCF": col("fcf_ttm_eok"), "영업이익": col("ebit_ttm_eok"), "자기자본": col("equity_eok"),
        "투자자본": col("invested_capital_eok"), "영업마진": col("op_margin_pct"),
        "ROIC": col("roic_pct_21"), "PBR": r2("pb"), "PER": r2("pe_trailing"), "경고": col("warn"),
        "매출성장률": col("rev_growth_fy_pct"), "FCF성장률": col("fcf_growth_fy_pct"),
    })
    paste.to_csv(out_dir("finance") / "sheet_paste_kr.csv", index=False, encoding="utf-8-sig")

    show = [c for c in ["ticker", "report", "market_cap_eok", "net_debt_eok", "fcf_ttm_eok",
                        "ebit_ttm_eok", "invested_capital_eok", "op_margin_pct", "roic_pct_21",
                        "warn"] if c in df.columns]
    print()
    print(df[show].to_string(index=False))
    print(f"\n저장: {out_dir('finance')} 의 fundamentals_kr.csv, sheet_paste_kr.csv (단위: 억원)")


if __name__ == "__main__":
    main()
