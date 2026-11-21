#!/usr/bin/env python3
"""fetch_sentiment.py - 시트 '📝 분위기 일지'용 데이터 수집 (사용자 PC에서 실행)

수집하는 것
  1) 고객예탁금·신용잔고 (네이버 증권 stock.naver.com API trendDeposit, 일별, 억원)
  2) 유가증권(코스피) 투자자별 순매수: 개인·외국인·기관 (네이버 증권 stock.naver.com API, 일별, 억원)
  3) 코스피 종가·거래량 (야후 ^KS11, 일별. 네이버 지수 페이지가 410이라 대체, 거래대금 없음)
  4) 검색량 (NAVER API HUB 검색어 트렌드, 주별, 선택: 키가 있을 때만)
  5) 구글 트렌드 (pytrends, 최근 5년 주별, 선택: pip install pytrends. 비공식 라이브러리라 막힐 수 있음)

못 하는 것 (손으로 채움)
  VKOSPI, 반대매매 금액, 레버리지·인버스 ETF 자금

사용법
  python fetch_sentiment.py                 # 최근 40일, 결과 요약 출력
  python fetch_sentiment.py --days 800      # 과거 비교용 대량 수집 (느림)
  python fetch_sentiment.py --selftest      # 네트워크 없이 코드 점검
  python fetch_sentiment.py --debug         # 표 열 이름 출력 (페이지 구조가 바뀐 것 같을 때)

키 (선택). 환경변수, 없으면 my-skills 공용 .env (OneDrive '96. 인증' 폴더)
  NAVER_CLIENT_ID=...
  NAVER_CLIENT_SECRET=...
  (invest 폴더는 구글 드라이브 동기화 폴더라 .env를 두면 키가 드라이브에 올라간다. 두지 말 것)
  (네이버 클라우드 플랫폼 콘솔에서 받은 NAVER API HUB 검색어 트렌드용 Client ID/Secret. 키는 대화창에 붙이지 말 것)

출력 (--out 폴더, 기본 공용 .env 의 PERSONAL_INVEST_SHEET__OUTPUT_DIR/sentiment_out)
  money_daily.csv   날짜별 예탁금·신용잔고·순매수·코스피
  search_weekly.csv 주별 검색량 (키가 있을 때)
  journal_hint.txt  일지 칸에 옮겨 적을 요약
"""
import argparse
import datetime as dt
import io
import os
import re
import sys
import time
import warnings

import pandas as pd
import requests

warnings.filterwarnings("ignore", category=FutureWarning)   # pytrends가 내는 pandas 경고(무해) 숨김

BASE = "https://finance.naver.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
PAUSE = 0.3          # 요청 사이 대기(초)
MAX_PAGES = 120      # 안전장치

# 검색량 키워드 그룹 (그룹당 최대 20개, 그룹 수 최대 5개). 여기서 고치면 됨.
SEARCH_GROUPS = {
    "주식": ["주식", "주식투자"],
    "빚투": ["빚투", "신용융자"],
    "반대매매": ["반대매매", "강제청산"],
    "코스피": ["코스피", "코스피 전망"],
    "후회": ["주식 후회", "주식 손절"],
}

DEBUG = False
WARNINGS = []


# ---------- 공통 ----------
def load_env(path=".env"):
    env = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def load_keys():
    """NAVER 키는 공용 .env (invest_common 이 불러올 때 환경변수로 넣음) 에서 읽는다."""
    import invest_common  # noqa: F401  (공용 .env -> os.environ)
    env = {}
    for k in ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def get_html(url, params=None, retries=3):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=15)
            r.raise_for_status()
            time.sleep(PAUSE)
            try:  # 네이버 페이지가 UTF-8로 바뀌었다. 실패하면 예전 EUC-KR로
                return r.content.decode("utf-8")
            except UnicodeDecodeError:
                return r.content.decode("euc-kr", errors="replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1 + i)
    raise RuntimeError(f"요청 실패: {url} ({last})")


def parse_date(s):
    m = re.match(r"\s*(\d{2,4})[.\-/](\d{1,2})[.\-/](\d{1,2})", str(s))
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None


def to_num(x):
    if x is None:
        return None
    s = re.sub(r"[,\s+▲▼]", "", str(x))
    s = s.replace("−", "-")
    try:
        return float(s)
    except ValueError:
        return None


def flat_cols(df):
    if isinstance(df.columns, pd.MultiIndex):
        cols = []
        for tup in df.columns:
            parts = [str(p) for p in tup if not str(p).startswith("Unnamed")]
            cols.append(" ".join(dict.fromkeys(parts)))
        df = df.copy()
        df.columns = cols
    else:
        df = df.copy()
        df.columns = [str(c) for c in df.columns]
    return df


def find_col(df, *keys):
    for c in df.columns:
        if all(k in c for k in keys):
            return c
    return None


def tables(html):
    try:
        return [flat_cols(t) for t in pd.read_html(io.StringIO(html), flavor="lxml")]
    except ValueError:  # 표가 없는 페이지(=마지막 페이지 너머)
        return []


def paged_rows(url, base_params, pick, cutoff, label):
    """페이지를 넘기며 pick(table)->list[dict]를 모으고 cutoff 이전 날짜가 나오면 멈춘다."""
    rows, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        params = dict(base_params, page=page)
        html = get_html(url, params)
        tabs = tables(html)
        if DEBUG and page == 1:
            for i, t in enumerate(tabs):
                print(f"[debug {label}] table {i} columns: {list(t.columns)} 행수={len(t)}")
                print(t.head(3).to_string())
        got = []
        for t in tabs:
            got = pick(t)
            if got:
                break
        if not got:
            break
        new = [r for r in got if r["date"] not in seen]
        if not new:
            break
        for r in new:
            seen.add(r["date"])
        rows.extend(new)
        if min(r["date"] for r in new) < cutoff:
            break
    if not rows:
        WARNINGS.append(f"{label}: 표를 읽지 못함 (--debug로 열 이름 확인)")
    return [r for r in rows if r["date"] >= cutoff]


# ---------- 1) 고객예탁금·신용잔고 ----------
def pick_deposit(t):
    dc, ec, cc = find_col(t, "날짜"), find_col(t, "예탁금"), find_col(t, "신용")
    if not (dc and ec and cc):
        return []
    out = []
    for _, r in t.iterrows():
        d = parse_date(r[dc])
        e, c = to_num(r[ec]), to_num(r[cc])
        if d and e is not None:
            out.append({"date": d, "deposit_eok": e, "credit_eok": c})
    return out


DEPOSIT_URL = "https://stock.naver.com/api/domestic/market/trendDeposit"
# 응답 content[]: bizdate, customerDeposit(고객예탁금), creditLoan(신용잔고). 단위는 억원으로 가정
# (11/11 customerDeposit 854843 = 85.5조). 옛 sise_deposit 페이지는 표가 비어 있어 이 API로 바꿨다.


def deposit_rows(content):
    """API content(list) -> [{date, deposit_eok, credit_eok}]"""
    out = []
    for item in content:
        try:
            d = dt.datetime.strptime(str(item.get("bizdate")), "%Y%m%d").date()
        except ValueError:
            continue
        dep = to_num(item.get("customerDeposit"))
        if dep is None:
            continue
        out.append({"date": d, "deposit_eok": dep, "credit_eok": to_num(item.get("creditLoan"))})
    return out


def fetch_deposit(cutoff, page_size=20):
    headers = dict(UA, Accept="application/json", Referer="https://stock.naver.com/market/stock/kr")
    rows, seen = [], set()
    for page in range(MAX_PAGES):
        params = {"startIdx": page * page_size, "pageSize": page_size}
        r = requests.get(DEPOSIT_URL, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        time.sleep(PAUSE)
        content = r.json().get("content") or []
        if DEBUG and page == 0 and content:
            print(f"[debug 예탁금·신용잔고] 첫 항목 키: {list(content[0].keys())}")
        new = [x for x in deposit_rows(content) if x["date"] not in seen]
        if not new:
            break
        seen.update(x["date"] for x in new)
        rows.extend(new)
        if min(x["date"] for x in new) < cutoff:
            break
    if not rows:
        WARNINGS.append("예탁금·신용잔고: 데이터를 읽지 못함 (--debug로 확인)")
    return [x for x in rows if x["date"] >= cutoff]


# ---------- 2) 투자자별 순매수 (코스피) ----------
INVESTOR_URL = "https://stock.naver.com/api/domestic/market/trend/daily"
# netAmounts.investorGubun 코드(화면 개인·기관 숫자와 대조해 맞춤): 8000 개인,
# 외국인 = 9000 외국인 + 9001 기타외국인,
# 기관 = 1000 금융투자 + 2000 보험 + 3000 투신 + 3100 사모 + 4000 은행 + 5000 기타금융 + 6000 연기금.
# 7100(기타법인)는 넣지 않는다. diffValue는 원 단위라 1억으로 나눠 억원으로 바꾼다.
INST_CODES = ("1000", "2000", "3000", "3100", "4000", "5000", "6000")


def investor_rows(content):
    """API content(list) -> [{date, indiv_eok, foreign_eok, inst_eok}]"""
    out = []
    for item in content:
        try:
            d = dt.datetime.strptime(str(item.get("bizdate")), "%Y%m%d").date()
        except ValueError:
            continue
        am = {a.get("investorGubun"): to_num(a.get("diffValue")) for a in item.get("netAmounts", [])}
        if am.get("8000") is None or am.get("9000") is None:
            continue
        inst = sum(am.get(c) or 0 for c in INST_CODES)
        out.append({"date": d, "indiv_eok": am["8000"] / 1e8,
                    "foreign_eok": (am["9000"] + (am.get("9001") or 0)) / 1e8,
                    "inst_eok": inst / 1e8})
    return out


def fetch_investor(cutoff, page_size=30):
    headers = dict(UA, Accept="application/json",
                   Referer="https://stock.naver.com/market/stock/kr/trend/trader")
    rows, seen = [], set()
    for page in range(MAX_PAGES):
        params = {"tradeType": "KRX", "marketType": "KOSPI",
                  "bizdate": dt.date.today().strftime("%Y%m%d"),
                  "startIdx": page * page_size, "pageSize": page_size}
        r = requests.get(INVESTOR_URL, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        time.sleep(PAUSE)
        content = r.json().get("content") or []
        if DEBUG and page == 0 and content:
            print(f"[debug 투자자별 순매수] 첫 항목 키: {list(content[0].keys())}")
        new = [x for x in investor_rows(content) if x["date"] not in seen]
        if not new:
            break
        seen.update(x["date"] for x in new)
        rows.extend(new)
        if min(x["date"] for x in new) < cutoff:
            break
    if not rows:
        WARNINGS.append("투자자별 순매수: 데이터를 읽지 못함 (--debug로 확인)")
    return [x for x in rows if x["date"] >= cutoff]


# ---------- 3) 코스피 지수 ----------
def pick_index(t):
    dc, pc = find_col(t, "날짜"), find_col(t, "체결가")
    vc, ac = find_col(t, "거래량"), find_col(t, "거래대금")
    if not (dc and pc):
        return []
    out = []
    for _, r in t.iterrows():
        d = parse_date(r[dc])
        p = to_num(r[pc])
        if d and p is not None:
            out.append({"date": d, "kospi": p,
                        "volume_k": to_num(r[vc]) if vc else None,
                        "value_m": to_num(r[ac]) if ac else None})
    return out


def fetch_index(cutoff):
    """코스피 종가·거래량. 네이버 sise_index_day가 410이라 야후(^KS11)로 대체한다. 거래대금은 없다."""
    try:
        import yfinance as yf
    except ImportError:
        WARNINGS.append("코스피 지수: yfinance가 없어 건너뜀 (pip install yfinance)")
        return []
    hist = yf.Ticker("^KS11").history(start=(cutoff - dt.timedelta(days=5)).isoformat(), auto_adjust=False)
    out = []
    for ts, r in hist.iterrows():
        d = ts.date()
        if d >= cutoff and pd.notna(r.get("Close")):
            vol = r.get("Volume")
            out.append({"date": d, "kospi": float(r["Close"]),
                        "volume_k": float(vol) / 1000 if pd.notna(vol) else None,
                        "value_m": None})
    if not out:
        WARNINGS.append("코스피 지수: 야후에서 데이터를 못 받음")
    return out


# ---------- 4) 네이버 데이터랩 검색량 ----------
ANCHOR = "코스피"   # 열끼리 비교할 때 기준으로 삼는 그룹


def _dl_post(cid, sec, start, end, groups):
    """그룹 이름 리스트로 한 번 요청 -> {그룹: Series(period->ratio)}. 실패하면 None.
    ratio는 이 요청에 든 모든 그룹을 통틀어 가장 큰 값이 100이다(요청마다 기준이 다름)."""
    body = {"startDate": start.isoformat(), "endDate": end.isoformat(), "timeUnit": "week",
            "keywordGroups": [{"groupName": g, "keywords": SEARCH_GROUPS[g]} for g in groups]}
    r = requests.post("https://naverapihub.apigw.ntruss.com/search-trend/v1/search",
                      headers={"X-NCP-APIGW-API-KEY-ID": cid, "X-NCP-APIGW-API-KEY": sec,
                               "Content-Type": "application/json"},
                      json=body, timeout=20)
    time.sleep(PAUSE)
    if r.status_code != 200:
        WARNINGS.append(f"데이터랩 오류 {r.status_code}: {r.text[:200]}")
        return None
    out = {}
    for res in r.json().get("results", []):
        out[res["title"]] = pd.Series({d["period"]: d["ratio"] for d in res["data"]}, dtype=float)
    if not out:
        WARNINGS.append(f"검색어 트렌드: 응답에 results가 없음 ({r.text[:200]})")
        return None
    return out


def fetch_datalab(env, start, end):
    """그룹마다 따로 요청해 각 열이 자기 최고점=100이 되게 한다(주별 비교용).
    '<그룹>_vs_코스피' 열은 코스피와 짝지어 받은 비율에 코스피 단독값을 곱해 공통 눈금으로 환산한 것(열끼리 비교용).
    start를 바꾸면 100의 기준(기간 내 최고점)이 바뀌므로 고정해서 쓸 것."""
    cid, sec = env.get("NAVER_CLIENT_ID"), env.get("NAVER_CLIENT_SECRET")
    if not (cid and sec):
        print("검색량: NAVER_CLIENT_ID/SECRET을 못 찾아 건너뜀 (환경변수 또는 OneDrive 96. 인증/.env)")
        return None
    own = {}
    for g in SEARCH_GROUPS:
        res = _dl_post(cid, sec, start, end, [g])
        if res is None or g not in res:
            return None
        own[g] = res[g]
    cols = dict(own)
    if ANCHOR in own:
        for g in SEARCH_GROUPS:
            if g == ANCHOR:
                continue
            res = _dl_post(cid, sec, start, end, [ANCHOR, g])
            if res is None or g not in res or ANCHOR not in res:
                return None
            rel = res[g] / res[ANCHOR].where(res[ANCHOR] > 0)   # 해당/기준: 요청의 최고점과 무관
            cols[f"{g}_vs_{ANCHOR}"] = (rel * own[ANCHOR]).round(5)
    df = pd.DataFrame(cols)
    df.index.name = "period"
    return df.reset_index()


# ---------- 5) 구글 트렌드 (pytrends, 비공식) ----------
# 구글 트렌드도 요청에 든 검색어 중 최고점이 100이라, 검색어마다 따로 요청한다(각 열 자기 최고점=100).
# 주별 데이터는 최근 5년까지만 나온다(더 길면 월별로 바뀜). 429(요청 과다)가 자주 나면 GT_PAUSE를 늘릴 것.
# '주식 후회'는 구글에서 값이 계속 0이라 뺐다(2026-11-15). 후회 검색량은 네이버 데이터랩 기준으로만 본다.
GT_TERMS = {"주식": "주식", "빚투": "빚투", "반대매매": "반대매매", "코스피": "코스피"}
GT_PAUSE = 3.0


def fetch_gtrends():
    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("구글 트렌드: pytrends가 없어 건너뜀 (pip install pytrends)")
        return None
    pt = TrendReq(hl="ko", tz=-540)
    cols = {}
    for name, term in GT_TERMS.items():
        try:
            pt.build_payload([term], timeframe="today 5-y", geo="KR")
            df = pt.interest_over_time()
        except Exception as e:  # noqa: BLE001
            WARNINGS.append(f"구글 트렌드 '{term}' 실패: {e}")
            time.sleep(GT_PAUSE)
            continue
        time.sleep(GT_PAUSE)
        if df is None or df.empty or term not in df:
            WARNINGS.append(f"구글 트렌드 '{term}': 데이터 없음")
            continue
        if "isPartial" in df:
            df = df[~df["isPartial"].astype(bool)]
        cols[name] = df[term].astype(float)
    if not cols:
        return None
    out = pd.DataFrame(cols)
    out.index = out.index.strftime("%Y-%m-%d")
    out.index.name = "period"
    return out.reset_index()


# ---------- 합치기·요약 ----------
def merge(dep, inv, idx):
    frames = []
    for rows in (dep, inv, idx):
        if rows:
            frames.append(pd.DataFrame(rows).set_index("date"))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1).sort_index(ascending=False).reset_index()


def jo(v_eok):
    return f"{v_eok / 10000:.1f}조" if v_eok is not None and pd.notna(v_eok) else "미확인"


def hint(df):
    if df.empty:
        return "수집된 데이터가 없습니다."
    out = []
    dep = df.dropna(subset=["deposit_eok"]) if "deposit_eok" in df else pd.DataFrame()
    if not dep.empty:
        r = dep.iloc[0]
        out.append(f"M열(돈): 예탁금 {jo(r['deposit_eok'])} ({r['date']} 기준)")
        if not (100_000 <= r["deposit_eok"] <= 3_000_000):
            WARNINGS.append("예탁금 값이 10조~300조 범위를 벗어남: 단위(억원) 가정이 틀렸을 수 있음")
        if "credit_eok" in dep and pd.notna(r["credit_eok"]):
            out.append(f"D열(돈): 신용잔고 {jo(r['credit_eok'])} ({r['date']} 기준)")
    if "indiv_eok" in df:
        inv = df.dropna(subset=["indiv_eok"])
        if not inv.empty:
            last5 = inv.head(5)
            out.append(
                f"D열(수급): 최근 {len(last5)}거래일 코스피 순매수(억원) "
                f"개인 {last5['indiv_eok'].sum():+,.0f}, 외국인 {last5['foreign_eok'].sum():+,.0f}, "
                f"기관 {last5['inst_eok'].sum():+,.0f} ({last5.iloc[-1]['date']}~{last5.iloc[0]['date']})")
    if "kospi" in df:
        ix = df.dropna(subset=["kospi"])
        if not ix.empty:
            r = ix.iloc[0]
            vol = f", 거래대금 {r['value_m'] / 1e6:.1f}조" if pd.notna(r.get("value_m")) else ""
            out.append(f"E열(가격): 코스피 {r['kospi']:,.2f} ({r['date']}){vol}. VKOSPI는 수기")
    return "\n".join(out)


# ---------- 셀프 테스트 ----------
def selftest():
    """네트워크 없이 파싱·병합·요약 코드가 도는지만 확인 (실제 페이지 구조 검증은 아님)."""
    today = dt.date.today()
    days = [today - dt.timedelta(days=i) for i in range(12)]
    dep_content = [{"bizdate": d.strftime("%Y%m%d"), "customerDeposit": str(974280 - i * 100),
                    "creditLoan": str(337057 + i)} for i, d in enumerate(days)]
    inv_content = [
        {"bizdate": d.strftime("%Y%m%d"), "netAmounts": [
            {"investorGubun": "8000", "diffValue": str(-i * 10 * 10**8)},
            {"investorGubun": "9000", "diffValue": str(i * 20 * 10**8)},
            {"investorGubun": "1000", "diffValue": str(i * 10**8)},
            {"investorGubun": "7100", "diffValue": "500000000"}]}
        for i, d in enumerate(days)]
    idx_rows = [{"date": d, "kospi": 5375.36 - i, "volume_k": 600000.0, "value_m": 15000000.0}
                for i, d in enumerate(days)]
    df = merge(deposit_rows(dep_content), investor_rows(inv_content), idx_rows)
    assert len(df) == 12, f"행 수 이상: {len(df)}"
    assert {"deposit_eok", "indiv_eok", "kospi"} <= set(df.columns)
    print(hint(df))
    print("selftest OK (가짜 표 기준)")


# ---------- main ----------
def main():
    global DEBUG
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=40, help="돌아볼 일수 (기본 40)")
    ap.add_argument("--out", default=None, help="결과 폴더 (기본: 공용 .env 의 OUTPUT_DIR/sentiment_out)")
    ap.add_argument("--search-start", default="2016-01-01", help="검색량 시작일 (주별). 바꾸면 100의 기준이 달라지니 고정 권장")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if not a.out:
        from invest_common import out_dir
        a.out = str(out_dir("sentiment"))
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    DEBUG = a.debug
    if a.selftest:
        selftest()
        return

    env = load_keys()
    cutoff = dt.date.today() - dt.timedelta(days=a.days)
    os.makedirs(a.out, exist_ok=True)

    results = {}
    for name, fn in (("dep", fetch_deposit), ("inv", fetch_investor), ("idx", fetch_index)):
        try:
            results[name] = fn(cutoff)
            print(f"{name}: {len(results[name])}행")
        except Exception as e:  # noqa: BLE001
            results[name] = []
            WARNINGS.append(f"{name} 실패: {e}")

    df = merge(results["dep"], results["inv"], results["idx"])
    if not df.empty:
        df.to_csv(os.path.join(a.out, "money_daily.csv"), index=False, encoding="utf-8-sig")

    try:
        sdf = fetch_datalab(env, dt.date.fromisoformat(a.search_start), dt.date.today())
        if sdf is not None:
            sdf.to_csv(os.path.join(a.out, "search_weekly.csv"), index=False, encoding="utf-8-sig")
            print(f"검색량: {len(sdf)}주 저장")
    except Exception as e:  # noqa: BLE001
        WARNINGS.append(f"검색량 실패: {e}")

    try:
        gdf = fetch_gtrends()
        if gdf is not None:
            gdf.to_csv(os.path.join(a.out, "google_trends_weekly.csv"), index=False, encoding="utf-8-sig")
            print(f"구글 트렌드: {len(gdf)}주 저장")
    except Exception as e:  # noqa: BLE001
        WARNINGS.append(f"구글 트렌드 실패: {e}")

    text = hint(df)
    with open(os.path.join(a.out, "journal_hint.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print("\n--- 일지 칸에 옮겨 적을 값 (기준일 꼭 함께 적기) ---")
    print(text)
    if WARNINGS:
        print("\n--- 경고 ---")
        for w in WARNINGS:
            print("-", w)


if __name__ == "__main__":
    main()
