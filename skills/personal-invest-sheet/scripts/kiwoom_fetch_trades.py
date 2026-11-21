#!/usr/bin/env python3
"""
키움 REST API → 투자시트 '📒 매매일지' 형식 변환기 (앱키에 연결된 키움 계좌)

데이터 소스
  국내  kt00015 위탁종합거래내역(gds_tp=1) : 결제 완료된 국내 매매
        kt00007 계좌별주문체결내역상세      : 국내 당일/미결제 체결 (--domestic 옵션일 때만)
  해외  ust21180 미국주식 기간별 주문내역    : 결제 전 당일 거래 포함, 체결수량/단가
        ust21070 미국주식 원장잔고확인       : 보유수량/매입단가/금일 매수·매도수량 (스냅샷)
        usa21670 미국주식 일별계좌수익률현황 : 날짜별 환율

사용법 (PC에서 실행):
    .env: KIWOOM_APPKEY=..., KIWOOM_SECRETKEY=...  (따옴표 없이)
    .env: my-skills 공용 .env 를 읽는다(invest_common). --env 파일은 거기에 없는 키만 보충. OS 환경변수가 가장 우선
    매매근거 태그: 공용 .env 의 PERSONAL_INVEST_SHEET__KIWOOM_TAG (기본 [키움])

    python kiwoom_fetch_trades.py                      # 최근 14일 ~ 오늘 (국내+해외)
    python kiwoom_fetch_trades.py --since 20261106     # 시작일 지정
    python kiwoom_fetch_trades.py --domestic           # 국내 당일/미결제도 조회
    python kiwoom_fetch_trades.py --mock               # 모의투자 서버

결과 (기본: invest/data/invest-output/):
    trades_raw_<since>_<until>.json    API 원본 응답 (검증용)
    trades_rows_<since>_<until>.tsv    매매일지 열 순서로 변환된 행 (_출처, _환율 포함)
    us_balance_<until>.tsv             미국주식 보유 스냅샷 (시트 포트폴리오와 대조용)
    → Claude가 이 파일을 읽어 시트에 중복 없이 추가합니다.

※ 키는 코드/출력/로그에 절대 남기지 않습니다.
"""
import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

REAL = "https://api.kiwoom.com"
MOCK = "https://mockapi.kiwoom.com"
from invest_common import kiwoom_tag, out_dir  # noqa: E402  (공용 .env 도 여기서 읽음)

TAG = kiwoom_tag()
ACNT = "/api/dostk/acnt"
US_ACNT = "/api/us/acnt"


# ------------------------------------------------------------------ 공통
def load_env(explicit=None):
    """.env를 직접 파싱(의존성 없음). 이미 설정된 환경변수는 덮어쓰지 않음."""
    candidates = [Path(explicit)] if explicit else []
    for c in candidates:
        if c.is_file():
            for line in c.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return str(c)
    return None


def get_token(base):
    appkey = os.environ.get("KIWOOM_APPKEY")
    secret = os.environ.get("KIWOOM_SECRETKEY")
    if not appkey or not secret:
        sys.exit(".env 또는 환경변수에 KIWOOM_APPKEY / KIWOOM_SECRETKEY 를 설정하세요.")
    r = requests.post(
        f"{base}/oauth2/token",
        headers={"Content-Type": "application/json;charset=UTF-8"},
        json={"grant_type": "client_credentials", "appkey": appkey, "secretkey": secret},
        timeout=15,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("return_code") not in (0, "0", None) or "token" not in body:
        sys.exit(f"토큰 발급 실패: {body}")
    return body["token"]


REQ_GAP = 0.3  # 요청 사이 최소 간격(초). 키움은 짧은 시간에 몰리면 429를 준다


def post(url, headers, body, timeout=20, tries=5):
    """429(요청 과다)면 1·2·4·8초 기다렸다 다시 보낸다. 다른 오류는 그대로 올린다."""
    for i in range(tries):
        time.sleep(REQ_GAP)
        r = requests.post(url, headers=headers, json=body, timeout=timeout)
        if r.status_code != 429 or i == tries - 1:
            r.raise_for_status()
            return r
        wait = 2 ** i
        print(f"  [대기] {headers.get('api-id')} 요청 과다(429), {wait}초 후 다시 시도", file=sys.stderr)
        time.sleep(wait)


def call(base, token, api_id, path, body, list_key):
    """연속조회(cont-yn/next-key)를 처리하며 list_key 배열을 모두 모아 반환."""
    out, cont, nxt = [], "N", ""
    while True:
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
            "api-id": api_id,
            "cont-yn": cont,
            "next-key": nxt,
        }
        r = post(f"{base}{path}", headers, body)
        data = r.json()
        if data.get("return_code") not in (0, "0"):
            raise RuntimeError(f"{api_id}: {data.get('return_code')} {data.get('return_msg')}")
        out.extend(data.get(list_key) or [])
        if r.headers.get("cont-yn") == "Y":
            cont, nxt = "Y", r.headers.get("next-key", "")
        else:
            break
    return out


def num(s):
    try:
        return float(str(s).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def season(d):
    # 시트의 기존 규칙에 맞춘 근사치: 1-2월 겨울, 3-5 봄, 6-8 여름, 9-12 가을
    m = d.month
    return "겨울" if m <= 2 else "봄" if m <= 5 else "여름" if m <= 8 else "가을"


def kr_code(raw):
    """국내: 'A005930' -> '5930' (시트는 앞자리 0 없이 저장)"""
    raw = (raw or "").strip()
    return (raw[1:] if raw[:1] == "A" else raw).lstrip("0") or "-"


def side_of(*texts):
    t = "".join(x or "" for x in texts)
    return "매수" if "매수" in t else "매도" if "매도" in t else ""


def make_row(d, name, code, side, qty, amount, note, cur, source, fx="", trade_no=""):
    pos_key = name if cur == "KRW" else code  # 시트 규칙: 국내=종목명, 해외=티커
    return {
        "매매일": f"{d.year}. {d.month}. {d.day}",
        "포지션ID": f"{pos_key}-{str(d.year)[2:]}년{season(d)}",
        "티커": code,
        "종목명": name,
        "구분": side,
        "수량": qty,
        "금액(원)": amount,
        "매매근거": note,
        "_거래번호": trade_no,
        "_통화": cur,
        "_출처": source,
        "_환율": fx,
        "_date": d,
    }


def weekdays(since, until):
    d, end = datetime.strptime(since, "%Y%m%d").date(), datetime.strptime(until, "%Y%m%d").date()
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def date_chunks(since, until, days):
    """API 조회기간 제한(kt00015: 1년, ust21180: 3개월) 때문에 구간을 나눈다."""
    s = datetime.strptime(since, "%Y%m%d").date()
    end = datetime.strptime(until, "%Y%m%d").date()
    while s <= end:
        e = min(s + timedelta(days=days - 1), end)
        yield s.strftime("%Y%m%d"), e.strftime("%Y%m%d")
        s = e + timedelta(days=1)


def call_chunked(base, token, api_id, path, make_body, list_key, since, until, days):
    """구간별로 조회해 합친다. 한 구간이 실패해도 나머지는 계속한다."""
    out = []
    for a, b in date_chunks(since, until, days):
        try:
            out.extend(call(base, token, api_id, path, make_body(a, b), list_key))
        except Exception as e:  # noqa: BLE001
            print(f"  [경고] {api_id} {a}~{b} 조회 실패: {e}")
    return out


# ------------------------------------------------------------------ 국내
def fetch_settled_domestic(base, token, since, until):
    def body(a, b):
        return {
            "strt_dt": a, "end_dt": b, "tp": "3",
            "stk_cd": "", "crnc_cd": "", "gds_tp": "1",   # 1: 국내주식
            "frgn_stex_code": "", "dmst_stex_tp": "%", "qry_sort_tp": "2",
        }
    return call_chunked(base, token, "kt00015", ACNT, body, "trst_ovrl_trde_prps_array",
                        since, until, 360)


def normalize_settled(rows):
    result = []
    for x in rows:
        side = x.get("io_tp_nm") or ""
        if side not in ("매수", "매도"):
            side = side_of(x.get("rmrk_nm"))
        if not side:
            continue  # 입출금/배당/이자 등 제외
        d_raw = (x.get("cntr_dt") or x.get("trde_dt") or "").strip()
        d = datetime.strptime(d_raw, "%Y%m%d").date()
        result.append(make_row(
            d, (x.get("stk_nm") or "").strip(), kr_code(x.get("stk_cd")), side,
            int(num(x.get("trde_qty_jwa_cnt"))), int(num(x.get("trde_amt"))),
            TAG, "KRW", "kt00015", "", x.get("trde_no", "")))
    return result


def fetch_domestic_by_day(base, token, since, until):
    """kt00007: 주문일자별 체결내역(체결만). 실패해도 전체를 멈추지 않음."""
    out = {}
    for d in weekdays(since, until):
        ds = d.strftime("%Y%m%d")
        body = {"ord_dt": ds, "qry_tp": "4", "stk_bond_tp": "1", "sell_tp": "0",
                "stk_cd": "", "fr_ord_no": "", "dmst_stex_tp": "%"}
        try:
            out[ds] = call(base, token, "kt00007", ACNT, body, "acnt_ord_cntr_prps_dtl")
        except Exception as e:  # noqa: BLE001
            print(f"  [경고] kt00007 {ds} 조회 실패: {e}")
            out[ds] = []
    return out


def normalize_domestic(by_day):
    result = []
    for ds, rows in by_day.items():
        d = datetime.strptime(ds, "%Y%m%d").date()
        for x in rows:
            qty = int(num(x.get("cntr_qty")))
            side = side_of(x.get("io_tp_nm"), x.get("trde_tp"))
            if qty <= 0 or not side:
                continue
            price = num(x.get("cntr_uv"))
            result.append(make_row(
                d, (x.get("stk_nm") or "").strip(), kr_code(x.get("stk_cd")), side, qty,
                int(round(qty * price)), f"{TAG} 체결단가 {price:,.0f}", "KRW",
                "kt00007", "", x.get("ord_no", "")))
    return result


def drop_already_settled(today_rows, settled_rows):
    """kt00015에 이미 같은 (날짜, 종목, 구분)이 있으면 kt00007 행은 버림."""
    have = defaultdict(int)
    for r in settled_rows:
        have[(r["_date"], r["티커"], r["구분"])] += r["수량"]
    return [r for r in today_rows if have.get((r["_date"], r["티커"], r["구분"]), 0) <= 0]


# ------------------------------------------------------------------ 해외 (미국주식)
def fetch_us_orders(base, token, since, until):
    """ust21180 기간별 주문내역 (체결수량 > 0 만 사용)."""
    def body(a, b):
        return {"strt_dt": a, "end_dt": b, "slby_tp": "0",
                "stex_tp": "", "stk_cd": "", "oppo_trde_tp": "%"}
    return call_chunked(base, token, "ust21180", US_ACNT, body, "result_list", since, until, 88)


def fetch_us_balance(base, token):
    return call(base, token, "ust21070", US_ACNT, {"stex_tp": "", "stk_cd": ""}, "result_list")


def fetch_us_daily(base, token, since, until):
    return call(base, token, "usa21670", US_ACNT, {"from": since, "to": until}, "result_list")


def call_raw(base, token, api_id, path, body):
    """리스트가 아닌 단일 응답(dict)을 그대로 반환."""
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": api_id, "cont-yn": "N", "next-key": "",
    }
    r = post(f"{base}{path}", headers, body)
    data = r.json()
    if data.get("return_code") not in (0, "0"):
        raise RuntimeError(f"{api_id}: {data.get('return_code')} {data.get('return_msg')}")
    return data


def fetch_us_cash(base, token):
    """ust21110 해외주식 예수금(외화예수금·주문가능), ust21160 결제 예정(D0~D4) 상세."""
    return {
        "ust21110": call_raw(base, token, "ust21110", US_ACNT, {}),
        "ust21160": call_raw(base, token, "ust21160", US_ACNT, {}),
    }


def build_fx_map(us_daily):
    return {str(x.get("base_dt", "")).strip(): num(x.get("exrt")) for x in us_daily if num(x.get("exrt")) > 0}


def normalize_us_orders(rows, fx_map, fallback_fx=0.0):
    result = []
    for x in rows:
        qty = int(num(x.get("cntr_qty")))
        side = side_of(x.get("slby_tp_nm"), x.get("trde_tp"))
        if qty <= 0 or not side:
            continue
        ds = str(x.get("ord_dt") or "").strip()
        us_d = datetime.strptime(ds, "%Y%m%d").date()
        # ord_dt는 미국 거래일. 시트는 한국 날짜 기준 → 새벽(12시 이전) 주문은 +1일
        d = us_d + timedelta(days=1) if str(x.get("ord_time") or "99:99:99") < "12:00:00" else us_d
        cur = (x.get("crnc_code") or "USD").strip() or "USD"
        usd = num(x.get("cntr_amt")) or qty * num(x.get("cntr_uv"))
        fx_val = fx_map.get(ds) or fallback_fx
        note = f"{TAG} {cur} {usd:,.2f}"
        if fx_val:
            amount = int(round(usd * fx_val))
            note += f" (환율 {fx_val:,.2f})"
        else:
            amount = 0
        row = make_row(
            d, (x.get("stk_nm") or "").strip(), (x.get("stk_cd") or "").strip() or "-",
            side, qty, amount, note, cur, "ust21180", fx_val or "", x.get("ord_no", ""))
        row["_미국거래일"] = ds
        row["_주문시간KST"] = x.get("ord_time", "")
        result.append(row)
    return result


BAL_COLS = ["티커", "종목명", "보유수량", "매입단가", "현재가", "전일매수", "전일매도",
            "금일매수", "금일매도", "환율", "매입단가(원)", "매입금액(원)"]


def balance_rows(rows):
    out = []
    for x in rows:
        out.append([
            (x.get("stk_cd") or "").strip(), (x.get("frgn_stk_nm") or "").strip(),
            x.get("poss_qty", ""), x.get("frgn_stk_book_uv", ""), x.get("now_pric", ""),
            x.get("pred_cntr_buyq", ""), x.get("pred_cntr_sellq", ""),
            x.get("tdy_cntr_buyq", ""), x.get("tdy_cntr_sellq", ""), x.get("exch_rate", ""),
            int(num(x.get("frgn_stk_book_uv_krw"))), int(num(x.get("frgn_stk_book_amt_krw")))])
    return out


# ------------------------------------------------------------------ main
def safe(label, fn, default):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        print(f"  [경고] {label} 조회 실패: {e}")
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=(date.today() - timedelta(days=14)).strftime("%Y%m%d"),
                    help="YYYYMMDD (기본: 14일 전)")
    ap.add_argument("--until", default=date.today().strftime("%Y%m%d"))
    ap.add_argument("--env", default=None, help=".env 경로")
    ap.add_argument("--mock", action="store_true", help="모의투자 서버 사용")
    ap.add_argument("--domestic", action="store_true", help="국내 당일/미결제 체결(kt00007)도 조회")
    ap.add_argument("--outdir", default=str(out_dir("kiwoom")))
    a = ap.parse_args()

    env_used = load_env(a.env)
    print(f".env: {env_used or '공용 .env'}")
    os.makedirs(a.outdir, exist_ok=True)
    base = MOCK if a.mock else REAL
    token = get_token(base)

    # 국내
    settled_raw = safe("국내 kt00015", lambda: fetch_settled_domestic(base, token, a.since, a.until), [])
    dom_raw = fetch_domestic_by_day(base, token, a.since, a.until) if a.domestic else {}
    settled = normalize_settled(settled_raw)
    dom_today = drop_already_settled(normalize_domestic(dom_raw), settled)

    # 해외
    us_orders_raw = safe("해외 ust21180", lambda: fetch_us_orders(base, token, a.since, a.until), [])
    us_bal_raw = safe("해외 ust21070", lambda: fetch_us_balance(base, token), [])
    us_daily = safe("해외 usa21670", lambda: fetch_us_daily(base, token, a.since, a.until), [])
    us_cash = safe("해외 예수금(ust21110/21160)", lambda: fetch_us_cash(base, token), {})
    fx_map = build_fx_map(us_daily)
    fallback_fx = next((num(x.get("exch_rate")) for x in us_bal_raw if num(x.get("exch_rate")) > 0), 0.0)
    us_rows = normalize_us_orders(us_orders_raw, fx_map, fallback_fx)

    rows = sorted(settled + dom_today + us_rows, key=lambda r: (r["_date"], r["_출처"]))

    tag = f"{a.since}_{a.until}"
    raw_path = os.path.join(a.outdir, f"trades_raw_{tag}.json")
    tsv_path = os.path.join(a.outdir, f"trades_rows_{tag}.tsv")
    bal_path = os.path.join(a.outdir, f"us_balance_{a.until}.tsv")

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({"kt00015": settled_raw, "kt00007": dom_raw, "ust21180": us_orders_raw,
                   "ust21070": us_bal_raw, "usa21670": us_daily, "us_cash": us_cash},
                  f, ensure_ascii=False, indent=2)

    cols = ["매매일", "포지션ID", "티커", "종목명", "구분", "수량", "금액(원)", "매매근거",
            "_거래번호", "_통화", "_출처", "_환율", "_미국거래일", "_주문시간KST"]
    with open(tsv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c, "") for c in cols])

    with open(bal_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(BAL_COLS)
        w.writerows(balance_rows(us_bal_raw))

    print(f"국내 {len(settled)}건(+당일 {len(dom_today)}건), 해외 {len(us_rows)}건 → 총 {len(rows)}건")
    tdy = [(b[0], b[7], b[8]) for b in balance_rows(us_bal_raw) if num(b[7]) or num(b[8])]
    for t, buy, sell in tdy:
        print(f"  [금일 해외 거래] {t}: 매수 {buy} / 매도 {sell}")
    for x in (us_cash.get("ust21110", {}) or {}).get("result_list", []) or []:
        print(f"  [해외 예수금] {x.get('crnc_code')}: 예수금 {x.get('fc_entra')} / 주문가능 {x.get('fc_ord_alowa')}")
    d160 = us_cash.get("ust21160", {}) or {}
    if d160:
        print(f"  [결제예정 USD] D0 {d160.get('d0_usd_fx_entr')} / D1 {d160.get('d1_usd_fx_entr')} / "
              f"D2 {d160.get('d2_usd_fx_entr')} (원화예수금 {d160.get('won_entr')})")
    print(f"  {raw_path}\n  {tsv_path}\n  {bal_path}")


if __name__ == "__main__":
    main()
