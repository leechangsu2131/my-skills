import streamlit as st
import pandas as pd
import requests
import time
import os
import json
from io import BytesIO
from math import radians, cos, sin, asin, sqrt
from itertools import product

# ──────────────────────────────────────────────
# 엑셀 안전 읽기 헬퍼
# (openpyxl이 custom-properties 버그로 실패하는 xlsx를
#  calamine → xlrd 순으로 자동 폴백)
# ──────────────────────────────────────────────

def _detect_engine(file_path_or_obj) -> str:
    """파일 확장자 기반 우선 엔진 결정"""
    try:
        name = getattr(file_path_or_obj, 'name', str(file_path_or_obj))
    except Exception:
        name = ""
    return 'xlrd' if name.lower().endswith('.xls') and not name.lower().endswith('.xlsx') else 'openpyxl'


def _calamine_available() -> bool:
    try:
        import python_calamine  # noqa
        return True
    except ImportError:
        return False


def safe_excel_file(file_path_or_obj):
    """pd.ExcelFile 대체 - openpyxl 실패 시 calamine → xlrd 자동 폴백"""
    preferred = _detect_engine(file_path_or_obj)
    engines = [preferred]
    if preferred != 'calamine' and _calamine_available():
        engines.insert(1, 'calamine')
    if 'xlrd' not in engines:
        engines.append('xlrd')

    last_err = None
    for eng in engines:
        try:
            return pd.ExcelFile(file_path_or_obj, engine=eng)
        except Exception as e:
            last_err = e
            # 업로드 파일(BytesIO-like)은 seek 후 재시도
            try:
                file_path_or_obj.seek(0)
            except Exception:
                pass
    raise last_err


def safe_read_excel(file_path_or_obj, sheet_name=0, header=0, engine=None, **kwargs):
    """pd.read_excel 대체 - openpyxl 실패 시 calamine → xlrd 자동 폴백"""
    preferred = engine or _detect_engine(file_path_or_obj)
    engines = [preferred]
    if preferred != 'calamine' and _calamine_available():
        engines.insert(1, 'calamine')
    if 'xlrd' not in engines:
        engines.append('xlrd')

    last_err = None
    for eng in engines:
        try:
            return pd.read_excel(file_path_or_obj, sheet_name=sheet_name,
                                 header=header, engine=eng, **kwargs)
        except Exception as e:
            last_err = e
            try:
                file_path_or_obj.seek(0)
            except Exception:
                pass
    raise last_err

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import folium
    from streamlit_folium import st_folium
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

st.set_page_config(page_title="스마트 경로 조회", page_icon="📍", layout="wide")

# ──────────────────────────────────────────────
# 스타일
# ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp {
        background: linear-gradient(180deg, #fff9e9 0%, #f4eeda 100%);
    }

    [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; color: #1e1c10; }

    .stTabs [data-baseweb="tab"] {
        font-size: 0.95rem;
        padding: 10px 16px;
        border-radius: 8px 8px 0 0;
    }
    .stTabs [aria-selected="true"] {
        font-weight: 700;
        color: #6a5f00;
        border-bottom: 3px solid #6a5f00;
    }

    div[data-testid="column"] { padding: 6px; }

    div[data-testid="stForm"] {
        background: #faf3df;
        border: 1px solid #e8e2cf;
        border-radius: 12px;
        padding: 16px;
    }

    .stButton>button {
        border-radius: 9999px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }
    .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }

    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 8px !important;
        border: 1px solid #cdc7aa !important;
        background: #faf3df !important;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #6a5f00 !important;
        box-shadow: 0 0 0 2px rgba(106,95,0,0.15) !important;
    }

    .stSelectbox>div>div, .stFileUploader>div>div {
        border-radius: 8px !important;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 12px;
        border: 1px solid #e8e2cf;
        overflow: hidden;
    }

    h2, h3 { color: #1e1c10; }
    .stCaption { color: #4b4732; }

    .info-box {
        background: #fee500;
        border-left: 4px solid #6a5f00;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
    }
    .card {
        background: #ffffff;
        border: 1px solid #e8e2cf;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

ENV_API_KEY = os.getenv("KAKAO_API_KEY", "")
HEADERS = {}

# ──────────────────────────────────────────────
# 카카오 API 함수
# ──────────────────────────────────────────────

def make_headers(key): return {"Authorization": f"KakaoAK {key}"}


def name_similarity(query: str, result: str) -> float:
    """쿼리와 검색결과 이름이 얼마나 비슷한지 0~1 반환"""
    q = query.replace(" ", "")
    r = result.replace(" ", "")
    if not q:
        return 0.0
    common = sum(1 for c in q if c in r)
    return common / len(q)


def search_address(query: str) -> tuple:
    """주소 검색 폴백 → (lng, lat, 주소, 장소명)"""
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    try:
        res = requests.get(url, headers=HEADERS, params={"query": query, "size": 1}, timeout=5)
        if res.status_code == 200:
            docs = res.json().get("documents", [])
            if docs:
                d = docs[0]
                x = float(d["x"]); y = float(d["y"])
                addr = d.get("road_address", {}).get("address_name") or d.get("address_name", "")
                return x, y, addr, addr
    except Exception:
        pass
    return None, None, None, None


def search_place(query: str, category_code: str = None, size: int = 5) -> tuple:
    """키워드 검색 → 유사도 기반 최적 결과 반환, 실패 시 주소 검색 폴백"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    codes = [category_code] if category_code else ["SC4", ""]
    for code in codes:
        params = {"query": query, "size": size}
        if code:
            params["category_group_code"] = code
        try:
            res = requests.get(url, headers=HEADERS, params=params, timeout=5)
            if res.status_code == 200:
                docs = res.json().get("documents", [])
                if docs:
                    best = max(docs, key=lambda d: name_similarity(query, d["place_name"]))
                    return (
                        float(best["x"]), float(best["y"]),
                        best.get("road_address_name") or best.get("address_name", ""),
                        best["place_name"],
                    )
        except Exception:
            pass
    # 폴백: 주소 검색
    return search_address(query)


def search_school(query: str) -> tuple:
    """학교 전용 검색 → (lng, lat, 주소, 장소명)"""
    return search_place(query, category_code="SC4")


def get_route(o_lng, o_lat, d_lng, d_lat, priority="RECOMMEND") -> tuple:
    """Directions API → (거리km, 소요시간분, 오류문자열)"""
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    params = {
        "origin": f"{o_lng},{o_lat}",
        "destination": f"{d_lng},{d_lat}",
        "priority": priority,
    }
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=8)
        if res.status_code in (401, 403):
            return None, None, (
                f"길찾기 API 인증 오류 ({res.status_code}) — "
                f"카카오 개발자 센터 → 내 애플리케이션 → [앱] → 제품 설정 → '카카오맵' 활성화 필요"
            )
        if res.status_code != 200:
            return None, None, f"HTTP {res.status_code}"
        routes = res.json().get("routes", [])
        if routes and routes[0].get("result_code") == 0:
            s = routes[0]["summary"]
            return round(s["distance"] / 1000, 1), int(s["duration"] / 60), ""
        return None, None, f"경로 없음 (code={routes[0].get('result_code') if routes else 'N/A'})"
    except Exception as e:
        return None, None, str(e)


def test_directions_api():
    """API 연결 테스트용 진단"""
    _, _, err = get_route(126.9784, 37.5665, 127.0276, 37.4979)
    return err


def get_route_with_waypoint(a_lng, a_lat, x_lng, x_lat, b_lng, b_lat, priority="RECOMMEND") -> tuple:
    """A → X → B 경유 경로 → (총거리km, 총시간분, 오류문자열)"""
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    params = {
        "origin": f"{a_lng},{a_lat}",
        "destination": f"{b_lng},{b_lat}",
        "waypoints": f"{x_lng},{x_lat}",
        "priority": priority,
    }
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=8)
        if res.status_code in (401, 403):
            return None, None, (
                f"길찾기 API 인증 오류 ({res.status_code}) — "
                f"카카오 개발자 센터 → 내 애플리케이션 → [앱] → 제품 설정 → '카카오맵' 활성화 필요"
            )
        if res.status_code != 200:
            return None, None, f"HTTP {res.status_code}"
        routes = res.json().get("routes", [])
        if routes and routes[0].get("result_code") == 0:
            s = routes[0]["summary"]
            return round(s["distance"] / 1000, 1), int(s["duration"] / 60), ""
        return None, None, f"경로 없음 (code={routes[0].get('result_code') if routes else 'N/A'})"
    except Exception as e:
        return None, None, str(e)


def haversine(lng1, lat1, lng2, lat2) -> float:
    R = 6371
    dlat, dlng = radians(lat2-lat1), radians(lng2-lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlng/2)**2
    return round(2*R*asin(sqrt(a)), 2)


def geocode_list(locations: list, prefix: str = "") -> list:
    """장소 이름 리스트 → [{name, lng, lat, addr}] 변환"""
    results = []
    for name in locations:
        q = f"{prefix} {name}".strip() if prefix else name
        lng, lat, addr, matched = search_place(q)
        results.append({
            "name": name, "query": q,
            "lng": lng, "lat": lat,
            "addr": addr, "matched": matched,
            "ok": lng is not None,
        })
        time.sleep(0.1)
    return results


# ──────────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────────

with st.sidebar:
    st.header("🔑 API 키 설정")
    if ENV_API_KEY:
        api_key = ENV_API_KEY
        st.success(f"✅ .env 로드됨 (...{api_key[-4:]})")
    else:
        st.markdown("[카카오 개발자 센터](https://developers.kakao.com) → REST API 키")
        api_key = st.text_input("Kakao REST API 키", type="password")

    if api_key:
        HEADERS.update(make_headers(api_key))
        if not ENV_API_KEY:
            st.success("✅ 입력 완료")

        st.divider()
        if st.button("🔬 길찾기 API 테스트", use_container_width=True):
            with st.spinner("테스트 중..."):
                err = test_directions_api()
            if not err:
                st.success("✅ 길찾기 API 정상")
            else:
                st.error(f"❌ {err}")
    else:
        st.warning("API 키를 입력하세요")

    st.divider()
    similarity_threshold = st.slider(
        "장소 유사도 임계점", 0.0, 1.0, 0.3, 0.05,
        help="검색 결과 이름이 입력 이름과 이 비율 이상 유사할 때만 매칭. 낮추면 유연, 높이면 엄격"
    )
    st.caption(f"현재 임계점: {similarity_threshold:.0%}")

    st.divider()
    priority = st.radio("경로 기준", ["RECOMMEND", "TIME", "DISTANCE"], index=0)
    st.divider()
    st.caption("📊 무료 한도\n- 키워드 검색: 300,000건/일\n- 길찾기: 300건/일")

    if not HAS_FOLIUM:
        st.divider()
        st.warning("지도 표시를 위해 설치 필요:\n```\npip install folium streamlit-folium\n```")


# ──────────────────────────────────────────────
# 탭 구성
# ──────────────────────────────────────────────

st.title("📍 스마트 경로 조회")
st.caption("카카오맵 기반 | 거리·소요시간 계산 · 다중 경로 매트릭스 · 최적 중간지점 탐색 · 경유지 비교")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚗 단일 출발 → 여러 장소",
    "🗂️ 여러 출발 → 여러 도착",
    "📍 최적 중간지점",
    "🛣️ 경유지 비교 (A→X→B)",
    "📋 수업나눔 일정 파서",
])


# ═══════════════════════════════════════════════
# TAB 1 : 단일 출발 → 여러 도착
# ═══════════════════════════════════════════════

with tab1:
    st.subheader("내 위치 → 엑셀의 여러 장소")

    # 파일 업로드
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    local_files = [f for f in os.listdir(DATA_DIR) if f.endswith((".xlsx", ".xls"))]

    src_mode = st.radio("파일 소스", ["📁 data 폴더", "📤 직접 업로드"], horizontal=True, key="t1_src")
    xl, file_src = None, None

    if src_mode == "📁 data 폴더":
        if local_files:
            sel = st.selectbox("파일 선택", local_files, key="t1_sel")
            file_src = os.path.join(DATA_DIR, sel)
            xl = safe_excel_file(file_src)
        else:
            st.warning("data/ 폴더에 엑셀 파일이 없습니다.")
    else:
        up = st.file_uploader("엑셀 업로드", type=["xlsx","xls"], key="t1_up")
        if up:
            file_src = up
            xl = safe_excel_file(up)

    if xl:
        c1, c2 = st.columns(2)
        with c1: sheet1 = st.selectbox("시트", xl.sheet_names, key="t1_sh")
        with c2: hrow1 = st.number_input("헤더 행", 1, value=1, key="t1_hr")
        df1 = safe_read_excel(file_src, sheet_name=sheet1, header=int(hrow1)-1)
        st.dataframe(df1.head(3), use_container_width=True)

        cols1 = list(df1.columns)
        ca, cb, cc = st.columns(3)
        with ca: place_col1 = st.selectbox("📌 장소명 열", cols1, key="t1_pc")
        with cb: time_col1  = st.selectbox("🕐 시간 열", cols1, index=min(1,len(cols1)-1), key="t1_tc")
        with cc: info_cols1 = st.multiselect("ℹ️ 추가 정보 열", [c for c in cols1 if c not in [place_col1, time_col1]], key="t1_ic")

        c1, c2 = st.columns(2)
        with c1: region1 = st.text_input("🗺️ 목적지 지역 접두사", placeholder="예: 경주", key="t1_rp")
        with c2: my_loc1 = st.text_input("🏠 출발 위치", placeholder="예: 경주역 / 경북 경주시 XX로 60", key="t1_my")
        my_prefix1 = st.text_input("출발 위치 지역 접두사 (선택)", placeholder="경주", key="t1_op")

        if st.button("🚀 계산 시작", type="primary", use_container_width=True, key="t1_btn",
                     disabled=not api_key or not my_loc1):

            my_query = f"{my_prefix1} {my_loc1}".strip() if my_prefix1 else my_loc1
            with st.spinner("출발 위치 조회 중..."):
                my_lng, my_lat, my_addr, _ = search_school(my_query)
                if not my_lng:
                    my_lng, my_lat, my_addr, _ = search_address(my_query)

            if not my_lng:
                st.error("출발 위치를 찾을 수 없습니다.")
                st.stop()
            st.success(f"✅ 출발: **{my_addr or my_loc1}**")

            rows1 = df1[df1[place_col1].notna()].copy()
            total1 = len(rows1)
            results1 = []
            directions_errors = []
            prog1 = st.progress(0, "조회 중...")
            dir_err_shown = False

            for i, (_, row) in enumerate(rows1.iterrows()):
                place = str(row[place_col1]).strip()
                q = f"{region1} {place}".strip() if region1 else place
                p_lng, p_lat, p_addr, matched = search_place(q)
                match_score = round(name_similarity(q, matched or ""), 2)
                time.sleep(0.1)

                dist_km, dur_min, note = None, None, ""
                if p_lng and match_score >= similarity_threshold:
                    dist_km, dur_min, err = get_route(my_lng, my_lat, p_lng, p_lat, priority)
                    time.sleep(0.15)
                    if err:
                        directions_errors.append(err)
                        if not dir_err_shown:
                            st.warning(f"⚠️ 길찾기 오류: {err} → 직선거리로 대체")
                            dir_err_shown = True
                        dist_km = haversine(my_lng, my_lat, p_lng, p_lat)
                        note = "직선거리"
                elif p_lng:
                    matched = f"❌ 유사도 낮음 ({match_score:.0%})"
                    p_lng = None; p_lat = None
                else:
                    matched = "❌ 미발견"

                res = {
                    "장소명": place, "검색결과": matched or "❌", "주소": p_addr or "",
                    "매칭점수": f"{match_score:.0%}",
                    "저장시간": row.get(time_col1, ""),
                    "거리(km)": dist_km if dist_km is not None else "-",
                    "소요시간(분)": dur_min if dur_min is not None else "-",
                    "비고": note,
                    "_lng": p_lng, "_lat": p_lat,
                }
                for c in info_cols1:
                    res[c] = row[c]
                results1.append(res)
                prog1.progress((i+1)/total1, f"({i+1}/{total1}) {place}")

            prog1.empty()
            rdf1 = pd.DataFrame(results1)
            ok1 = rdf1[rdf1["거리(km)"] != "-"]

            if directions_errors:
                err_summary = "\n".join(set(directions_errors[:3]))
                st.error(f"⚠️ 길찾기 API 오류 (총 {len(directions_errors)}건):\n{err_summary}")

            m1c, m2c, m3c, m4c = st.columns(4)
            m1c.metric("전체", f"{total1}곳")
            m2c.metric("성공", f"{len(ok1)}곳")
            m3c.metric("실패", f"{total1-len(ok1)}곳")
            if len(ok1): m4c.metric("평균 거리", f"{ok1['거리(km)'].mean():.1f}km")

            sort1 = st.radio("정렬", ["거리(km)", "소요시간(분)", "저장시간"], horizontal=True, key="t1_sort")
            ok_s = ok1.copy()
            try: ok_s = ok_s.sort_values(sort1)
            except: pass
            disp1 = pd.concat([ok_s, rdf1[rdf1["거리(km)"]=="-"]], ignore_index=True)

            def hl(v):
                if v=="-": return "color:#aaa"
                try:
                    f=float(v)
                    return "color:#0a8a0a;font-weight:bold" if f<=5 else ("color:#e67e00" if f<=15 else "color:#cc3300")
                except: return ""

            show_cols = [c for c in disp1.columns if not c.startswith("_")]
            try: styled1 = disp1[show_cols].style.map(hl, subset=["거리(km)"])
            except: styled1 = disp1[show_cols].style.applymap(hl, subset=["거리(km)"])
            st.dataframe(styled1, use_container_width=True, hide_index=True)
            st.caption("🟢≤5km 🟠5~15km 🔴>15km | 직선거리: 길찾기 미응답 시 대체")

            # 지도
            if HAS_FOLIUM and ok1["_lng"].notna().any():
                st.subheader("🗺️ 지도")
                m = folium.Map(location=[my_lat, my_lng], zoom_start=11)
                folium.Marker([my_lat, my_lng], popup="출발지",
                              icon=folium.Icon(color="red", icon="home")).add_to(m)
                for _, r in disp1.iterrows():
                    if r["_lat"]:
                        popup = f"{r['장소명']}<br>{r['거리(km)']}km / {r['소요시간(분)']}분"
                        folium.Marker([r["_lat"], r["_lng"]], popup=popup,
                                      icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)
                        folium.PolyLine([[my_lat, my_lng], [r["_lat"], r["_lng"]]],
                                        color="#3388ff", weight=1.5, opacity=0.5).add_to(m)
                st_folium(m, use_container_width=True, height=450, returned_objects=[], key="tab1_map")

            # 다운로드
            buf = BytesIO()
            disp1[show_cols].to_excel(buf, index=False)
            buf.seek(0)
            st.download_button("⬇️ 결과 엑셀 다운로드", buf, "결과_단일출발.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════
# TAB 2 : 여러 출발 → 여러 도착 (매트릭스)
# ═══════════════════════════════════════════════

with tab2:
    st.subheader("여러 출발지 × 여러 도착지 — 전체 경로 매트릭스")
    st.caption("각 출발지에서 각 목적지까지 소요시간을 표로 계산합니다.")

    t2_mode = st.radio("입력 방식", ["📝 직접 입력", "📁 엑셀 파일"], horizontal=True, key="t2_mode")

    origins_raw, dests_raw = "", ""
    ori_prefix, dst_prefix = "", ""

    if t2_mode == "📝 직접 입력":
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("**🟥 출발지 목록**")
            origins_raw = st.text_area(
                "출발지 (한 줄에 하나씩)",
                placeholder="경주역\n경주 황성공원\n경북 경주시 건천읍 XX로 60",
                height=140, key="t2_ori"
            )
            ori_prefix = st.text_input("출발지 지역 접두사 (선택)", placeholder="경주", key="t2_op")
        with col_r:
            st.markdown("**🟦 도착지 목록**")
            dests_raw = st.text_area(
                "도착지 (한 줄에 하나씩)",
                placeholder="건천초등학교\n황성초등학교\n용황초등학교\n흥무초등학교",
                height=140, key="t2_dst"
            )
            dst_prefix = st.text_input("도착지 지역 접두사 (선택)", placeholder="경주", key="t2_dp")
    else:
        src2 = st.radio("파일 소스", ["📁 data 폴더", "📤 직접 업로드"], horizontal=True, key="t2_src")
        xl2, file_src2 = None, None
        if src2 == "📁 data 폴더":
            local_files2 = [f for f in os.listdir(DATA_DIR) if f.endswith((".xlsx", ".xls"))]
            if local_files2:
                sel2 = st.selectbox("파일 선택", local_files2, key="t2_sel")
                file_src2 = os.path.join(DATA_DIR, sel2)
                xl2 = safe_excel_file(file_src2)
            else:
                st.warning("data/ 폴더에 엑셀 파일이 없습니다.")
        else:
            up2 = st.file_uploader("엑셀 업로드", type=["xlsx","xls"], key="t2_up")
            if up2:
                file_src2 = up2
                xl2 = safe_excel_file(up2)

        if xl2:
            c1, c2 = st.columns(2)
            with c1: sheet2 = st.selectbox("시트", xl2.sheet_names, key="t2_sh")
            with c2: hrow2 = st.number_input("헤더 행", 1, value=1, key="t2_hr")
            df2 = safe_read_excel(file_src2, sheet_name=sheet2, header=int(hrow2)-1)
            st.dataframe(df2.head(3), use_container_width=True, key="t2_preview")
            cols2 = list(df2.columns)
            c1, c2 = st.columns(2)
            with c1:
                ori_col = st.selectbox("🟥 출발지 열", cols2, key="t2_oc")
                ori_prefix = st.text_input("출발지 지역 접두사", placeholder="경주", key="t2_op2")
            with c2:
                dst_col = st.selectbox("🟦 도착지 열", cols2, key="t2_dc")
                dst_prefix = st.text_input("도착지 지역 접두사", placeholder="경주", key="t2_dp2")
            origins_raw = "\n".join(df2[ori_col].dropna().astype(str).tolist())
            dests_raw   = "\n".join(df2[dst_col].dropna().astype(str).tolist())
            st.caption(f"출발지 {len(df2[ori_col].dropna())}곳, 도착지 {len(df2[dst_col].dropna())}곳 로드됨")

    if st.button("🚀 매트릭스 계산", type="primary", use_container_width=True, key="t2_btn",
                 disabled=not api_key or not origins_raw.strip() or not dests_raw.strip()):

        origins = [x.strip() for x in origins_raw.strip().splitlines() if x.strip()]
        dests   = [x.strip() for x in dests_raw.strip().splitlines()   if x.strip()]

        total_calls = len(origins) * len(dests)
        st.info(f"API 호출 예정: **{total_calls}건** (하루 무료 한도 300건)")

        with st.spinner("출발지 좌표 조회 중..."):
            ori_info = geocode_list(origins, ori_prefix)
        with st.spinner("도착지 좌표 조회 중..."):
            dst_info = geocode_list(dests, dst_prefix)

        # 좌표 실패 표시
        fail_o = [o["name"] for o in ori_info if not o["ok"]]
        fail_d = [d["name"] for d in dst_info if not d["ok"]]
        if fail_o: st.warning(f"⚠️ 출발지 미발견: {', '.join(fail_o)}")
        if fail_d: st.warning(f"⚠️ 도착지 미발견: {', '.join(fail_d)}")

        ok_ori = [o for o in ori_info if o["ok"]]
        ok_dst = [d for d in dst_info if d["ok"]]

        if not ok_ori or not ok_dst:
            st.error("유효한 출발지·도착지가 없어 계산할 수 없습니다.")
            st.stop()

        # 매트릭스 계산
        dist_mat  = {o["name"]: {} for o in ok_ori}
        time_mat  = {o["name"]: {} for o in ok_ori}
        note_mat  = {o["name"]: {} for o in ok_ori}
        dir_err_shown2 = False

        total2 = len(ok_ori) * len(ok_dst)
        prog2 = st.progress(0, "매트릭스 계산 중...")
        cnt2 = 0

        for o in ok_ori:
            for d in ok_dst:
                dist_km, dur_min, err = get_route(o["lng"], o["lat"], d["lng"], d["lat"], priority)
                time.sleep(0.15)
                if err:
                    if not dir_err_shown2:
                        st.warning(f"⚠️ 길찾기 오류: {err} → 직선거리 대체")
                        dir_err_shown2 = True
                    dist_km = haversine(o["lng"], o["lat"], d["lng"], d["lat"])
                    note_mat[o["name"]][d["name"]] = "직선"
                else:
                    note_mat[o["name"]][d["name"]] = ""

                dist_mat[o["name"]][d["name"]] = dist_km
                time_mat[o["name"]][d["name"]] = dur_min

                cnt2 += 1
                prog2.progress(cnt2/total2, f"({cnt2}/{total2}) {o['name']} → {d['name']}")

        prog2.empty()

        # 소요시간 매트릭스 표
        st.subheader("⏱️ 소요시간 매트릭스 (분)")
        dst_names = [d["name"] for d in ok_dst]
        ori_names = [o["name"] for o in ok_ori]

        time_df = pd.DataFrame(index=ori_names, columns=dst_names)
        dist_df = pd.DataFrame(index=ori_names, columns=dst_names)
        for o in ori_names:
            for d in dst_names:
                t = time_mat[o].get(d)
                km = dist_mat[o].get(d)
                note = note_mat[o].get(d, "")
                time_df.loc[o, d] = f"{t}분" if t else (f"{km}km(직선)" if km else "-")
                dist_df.loc[o, d] = f"{km}km" if km else "-"
                if note == "직선" and km:
                    time_df.loc[o, d] = f"{km}km★"

        st.dataframe(time_df, use_container_width=True)
        st.caption("★ 표시: 길찾기 실패로 직선거리 표시")

        st.subheader("📏 거리 매트릭스 (km)")
        st.dataframe(dist_df, use_container_width=True)

        # 지도
        if HAS_FOLIUM:
            st.subheader("🗺️ 지도")
            center_lat = sum(o["lat"] for o in ok_ori + ok_dst) / (len(ok_ori)+len(ok_dst))
            center_lng = sum(o["lng"] for o in ok_ori + ok_dst) / (len(ok_ori)+len(ok_dst))
            m2 = folium.Map(location=[center_lat, center_lng], zoom_start=11)
            for o in ok_ori:
                folium.Marker([o["lat"], o["lng"]], popup=f"출발: {o['name']}",
                              icon=folium.Icon(color="red", icon="home")).add_to(m2)
            for d in ok_dst:
                folium.Marker([d["lat"], d["lng"]], popup=f"도착: {d['name']}",
                              icon=folium.Icon(color="blue", icon="flag")).add_to(m2)
            for o in ok_ori:
                for d in ok_dst:
                    if d["name"] in time_mat[o["name"]]:
                        folium.PolyLine([[o["lat"],o["lng"]],[d["lat"],d["lng"]]],
                                        color="#888", weight=1, opacity=0.4).add_to(m2)
            st_folium(m2, use_container_width=True, height=450, returned_objects=[], key="tab2_map")

        # 다운로드
        buf2 = BytesIO()
        with pd.ExcelWriter(buf2, engine="openpyxl") as writer:
            time_df.to_excel(writer, sheet_name="소요시간")
            dist_df.to_excel(writer, sheet_name="거리")
        buf2.seek(0)
        st.download_button("⬇️ 매트릭스 엑셀 다운로드", buf2, "매트릭스_결과.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════
# TAB 3 : 최적 중간지점 찾기
# ═══════════════════════════════════════════════

with tab3:
    st.subheader("📍 최적 중간지점 탐색")
    st.caption("여러 사람의 위치를 입력하면 — 총 이동시간이 가장 적은 중간 지점을 찾아드립니다.")

    t3_ppl_mode = st.radio("참여자 입력 방식", ["📝 직접 입력", "📁 엑셀 파일"], horizontal=True, key="t3_ppl_mode")

    people_raw = ""
    people_prefix = ""

    if t3_ppl_mode == "📝 직접 입력":
        st.markdown("**👥 참여자 위치 입력** (한 줄에 하나씩)")
        people_raw = st.text_area(
            "이름: 위치 (또는 위치만)",
            placeholder="홍길동: 경주역\n김철수: 경주 외동읍\n이영희: 경주 건천읍",
            height=160, key="t3_ppl"
        )
        people_prefix = st.text_input("참여자 지역 접두사 (선택)", placeholder="경주", key="t3_pp")
    else:
        src_mode_p = st.radio("파일 소스", ["📁 data 폴더", "📤 직접 업로드"], horizontal=True, key="t3_psrc")
        xl_p, file_src_p = None, None
        if src_mode_p == "📁 data 폴더":
            local_files_p = [f for f in os.listdir(DATA_DIR) if f.endswith((".xlsx", ".xls"))]
            if local_files_p:
                sel_p = st.selectbox("파일 선택", local_files_p, key="t3_psel")
                file_src_p = os.path.join(DATA_DIR, sel_p)
                xl_p = safe_excel_file(file_src_p)
            else:
                st.warning("data/ 폴더에 엑셀 파일이 없습니다.")
        else:
            up_p = st.file_uploader("엑셀 업로드", type=["xlsx","xls"], key="t3_pup")
            if up_p:
                file_src_p = up_p
                xl_p = safe_excel_file(up_p)

        if xl_p:
            c1, c2 = st.columns(2)
            with c1: sheet_p = st.selectbox("시트", xl_p.sheet_names, key="t3_psh")
            with c2: hrow_p = st.number_input("헤더 행", 1, value=1, key="t3_phr")
            df_p = safe_read_excel(file_src_p, sheet_name=sheet_p, header=int(hrow_p)-1)
            st.dataframe(df_p.head(3), use_container_width=True, key="t3_ppreview")
            cols_p = list(df_p.columns)
            c1, c2 = st.columns(2)
            with c1:
                name_col = st.selectbox("👤 이름 열", cols_p, key="t3_pnc")
                people_prefix = st.text_input("참여자 지역 접두사", placeholder="경주", key="t3_pp2")
            with c2:
                loc_col = st.selectbox("📍 위치 열", cols_p, key="t3_plc")
            lines = []
            for _, row in df_p.iterrows():
                if pd.notna(row[name_col]) and pd.notna(row[loc_col]):
                    lines.append(f"{row[name_col]}: {row[loc_col]}")
            people_raw = "\n".join(lines)
            st.caption(f"참여자 {len(lines)}명 로드됨")

    st.divider()
    st.markdown("**🎯 후보 중간지점 설정**")
    cand_mode = st.radio(
        "후보 방식",
        ["📋 엑셀 장소 중에서 선택 (A안)", "🌐 지도 격자 탐색 (B안)", "🔀 둘 다 (A+B)"],
        key="t3_mode"
    )

    xl3, file_src3 = None, None
    cand_places = []

    if cand_mode in ["📋 엑셀 장소 중에서 선택 (A안)", "🔀 둘 다 (A+B)"]:
        local_files3 = [f for f in os.listdir(DATA_DIR) if f.endswith((".xlsx", ".xls"))]
        src3 = st.radio("파일 소스", ["📁 data 폴더", "📤 직접 업로드"], horizontal=True, key="t3_src")
        if src3 == "📁 data 폴더":
            if local_files3:
                sel3 = st.selectbox("파일 선택", local_files3, key="t3_sel")
                file_src3 = os.path.join(DATA_DIR, sel3)
                xl3 = safe_excel_file(file_src3)
        else:
            up3 = st.file_uploader("엑셀 업로드", type=["xlsx","xls"], key="t3_up")
            if up3:
                file_src3, xl3 = up3, safe_excel_file(up3)

        if xl3:
            c1, c2 = st.columns(2)
            with c1: sheet3 = st.selectbox("시트", xl3.sheet_names, key="t3_sh")
            with c2: hrow3 = st.number_input("헤더 행", 1, value=1, key="t3_hr")
            df3 = safe_read_excel(file_src3, sheet_name=sheet3, header=int(hrow3)-1)
            cols3 = list(df3.columns)
            place_col3 = st.selectbox("📌 장소명 열", cols3, key="t3_pc")
            cand_prefix3 = st.text_input("후보지 지역 접두사 (선택)", placeholder="경주", key="t3_cp")
            cand_places = df3[place_col3].dropna().astype(str).tolist()
            st.caption(f"후보 장소 {len(cand_places)}곳 로드됨")

    grid_step = 0.02
    if cand_mode in ["🌐 지도 격자 탐색 (B안)", "🔀 둘 다 (A+B)"]:
        grid_step = st.slider("격자 간격 (도, 작을수록 정밀·느림)", 0.01, 0.1, 0.03, 0.01, key="t3_gs")

    top_n = st.number_input("상위 N개 후보에 대해 실제 길찾기 수행", 1, 20, 5, key="t3_tn",
                            help="직선거리로 추린 후 상위 N개만 실제 API 호출 → API 절약")

    if st.button("🔍 최적 중간지점 탐색", type="primary", use_container_width=True, key="t3_btn",
                 disabled=not api_key or not people_raw.strip()):

        # 참여자 파싱 및 좌표 조회
        people_lines = [x.strip() for x in people_raw.strip().splitlines() if x.strip()]
        people_names, people_locs = [], []
        for line in people_lines:
            if ":" in line:
                n, loc = line.split(":", 1)
                people_names.append(n.strip()); people_locs.append(loc.strip())
            else:
                people_names.append(f"참여자{len(people_names)+1}"); people_locs.append(line)

        with st.spinner("참여자 위치 조회 중..."):
            people_info = geocode_list(people_locs, people_prefix)

        for i, p in enumerate(people_info):
            p["label"] = people_names[i]

        fail_p = [p["label"] for p in people_info if not p["ok"]]
        if fail_p:
            st.warning(f"⚠️ 위치 미발견: {', '.join(fail_p)}")

        ok_people = [p for p in people_info if p["ok"]]
        if len(ok_people) < 2:
            st.error("최소 2명 이상의 위치가 필요합니다.")
            st.stop()

        # 중심점 계산
        center_lat = sum(p["lat"] for p in ok_people) / len(ok_people)
        center_lng = sum(p["lng"] for p in ok_people) / len(ok_people)
        span_lat   = max(p["lat"] for p in ok_people) - min(p["lat"] for p in ok_people)
        span_lng   = max(p["lng"] for p in ok_people) - min(p["lng"] for p in ok_people)

        # 후보지 수집
        candidates = []  # [{name, lng, lat, addr}]

        # A안: 엑셀 장소
        if cand_mode in ["📋 엑셀 장소 중에서 선택 (A안)", "🔀 둘 다 (A+B)"] and cand_places:
            with st.spinner(f"엑셀 후보 {len(cand_places)}곳 좌표 조회 중..."):
                for p in cand_places:
                    q = f"{cand_prefix3} {p}".strip() if (xl3 and 'cand_prefix3' in dir()) else p
                    lng, lat, addr, matched = search_place(q)
                    if lng:
                        candidates.append({"name": p, "lng": lng, "lat": lat, "addr": addr, "src": "엑셀"})
                    time.sleep(0.08)

        # B안: 격자
        if cand_mode in ["🌐 지도 격자 탐색 (B안)", "🔀 둘 다 (A+B)"]:
            pad = max(span_lat, span_lng) * 0.3 + grid_step
            lat_range = [round(center_lat - pad + i*grid_step, 6)
                         for i in range(int(2*pad/grid_step)+1)]
            lng_range = [round(center_lng - pad + i*grid_step, 6)
                         for i in range(int(2*pad/grid_step)+1)]
            grid_pts = list(product(lat_range, lng_range))
            for glat, glng in grid_pts:
                candidates.append({
                    "name": f"격자({glat:.3f},{glng:.3f})",
                    "lng": glng, "lat": glat, "addr": "", "src": "격자"
                })
            st.info(f"격자 후보: {len(grid_pts)}점")

        if not candidates:
            st.error("후보 지점이 없습니다. 엑셀 파일을 선택하거나 격자 방식을 사용하세요.")
            st.stop()

        # STEP 1: 직선거리로 총 거리 계산 → 빠른 사전 필터
        st.info(f"총 {len(candidates)}개 후보 중 → 직선거리로 상위 {top_n}개 추린 뒤 실제 경로 계산")
        for c in candidates:
            c["total_straight"] = sum(haversine(p["lng"], p["lat"], c["lng"], c["lat"]) for p in ok_people)

        candidates.sort(key=lambda c: c["total_straight"])
        top_candidates = candidates[:top_n]

        # STEP 2: 상위 후보에 대해 실제 길찾기
        total_api = len(ok_people) * len(top_candidates)
        st.info(f"실제 길찾기 API 호출: {total_api}건")
        prog3 = st.progress(0, "최적 지점 계산 중...")
        cnt3 = 0
        dir_err_shown3 = False

        for c in top_candidates:
            total_t, total_d, any_fail = 0, 0, False
            for p in ok_people:
                dist_km, dur_min, err = get_route(p["lng"], p["lat"], c["lng"], c["lat"], priority)
                time.sleep(0.15)
                if err:
                    if not dir_err_shown3:
                        st.warning(f"⚠️ 길찾기 오류: {err} → 직선거리로 대체")
                        dir_err_shown3 = True
                    dist_km = haversine(p["lng"], p["lat"], c["lng"], c["lat"])
                    any_fail = True
                total_t += (dur_min or 0)
                total_d += (dist_km or 0)
                cnt3 += 1
                prog3.progress(cnt3/total_api, f"계산 중... ({cnt3}/{total_api})")

            c["total_time"] = total_t
            c["total_dist"] = round(total_d, 1)
            c["note"] = "직선포함" if any_fail else ""

        prog3.empty()
        top_candidates.sort(key=lambda c: c["total_time"])

        # 결과 출력
        best = top_candidates[0]
        st.success(f"🏆 최적 중간지점: **{best['name']}**")
        if best["addr"]:
            st.caption(f"주소: {best['addr']}")

        r1, r2, r3 = st.columns(3)
        r1.metric("총 이동시간 합계", f"{best['total_time']}분")
        r2.metric("총 이동거리 합계", f"{best['total_dist']}km")
        r3.metric("후보 중 순위", f"1 / {len(top_candidates)}")

        # 후보 비교 표
        st.subheader("📊 후보지 비교")
        cand_df = pd.DataFrame([{
            "순위": i+1,
            "장소": c["name"],
            "출처": c["src"],
            "총이동시간(분)": c["total_time"],
            "총이동거리(km)": c["total_dist"],
            "직선거리합(km)": round(c["total_straight"], 1),
            "비고": c["note"],
        } for i, c in enumerate(top_candidates)])
        st.dataframe(cand_df, use_container_width=True, hide_index=True)

        # 지도
        if HAS_FOLIUM:
            st.subheader("🗺️ 지도")
            m3 = folium.Map(location=[best["lat"], best["lng"]], zoom_start=12)

            # 최적 지점 (금색 별)
            folium.Marker(
                [best["lat"], best["lng"]],
                popup=f"🏆 최적: {best['name']}<br>총 {best['total_time']}분",
                icon=folium.Icon(color="orange", icon="star"),
            ).add_to(m3)

            # 참여자 마커 + 선
            colors = ["red","purple","darkred","cadetblue","darkblue","green"]
            for i, p in enumerate(ok_people):
                color = colors[i % len(colors)]
                d_km, d_min, _ = get_route(p["lng"], p["lat"], best["lng"], best["lat"], priority)
                label = f"{p['label']}<br>→ 최적지: {d_km or '?'}km / {d_min or '?'}분"
                folium.Marker([p["lat"], p["lng"]], popup=label,
                              icon=folium.Icon(color=color, icon="user")).add_to(m3)
                folium.PolyLine([[p["lat"], p["lng"]], [best["lat"], best["lng"]]],
                                color=color, weight=2.5, opacity=0.7,
                                tooltip=f"{p['label']} → {best['name']}").add_to(m3)
                time.sleep(0.1)

            # 상위 후보 2~5위
            for c in top_candidates[1:5]:
                folium.CircleMarker(
                    [c["lat"], c["lng"]], radius=6,
                    popup=f"{c['name']}<br>총 {c['total_time']}분",
                    color="#888", fill=True, fill_opacity=0.5,
                ).add_to(m3)

            st_folium(m3, use_container_width=True, height=500, returned_objects=[], key="tab3_map")

        # 다운로드
        buf3 = BytesIO()
        cand_df.to_excel(buf3, index=False)
        buf3.seek(0)
        st.download_button("⬇️ 결과 엑셀 다운로드", buf3, "중간지점_결과.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════
# TAB 4 : 경유지 비교 (A → X → B)
# ═══════════════════════════════════════════════

with tab4:
    st.subheader("🛣️ 경유지 비교 (A → X → B)")
    st.caption("고정 출발지 A(근무지)와 고정 도착지 B(집) 사이에 경유지 X 후보를 넣었을 때 총 소요시간을 비교합니다.")

    c1, c2 = st.columns(2)
    with c1:
        a_loc = st.text_input("🅐 출발지 (근무지)", placeholder="경주 ○○초등학교", key="t4_a")
        a_prefix = st.text_input("A 지역 접두사 (선택)", placeholder="경주", key="t4_ap")
    with c2:
        b_loc = st.text_input("🅑 도착지 (집)", placeholder="경주시 ○○동", key="t4_b")
        b_prefix = st.text_input("B 지역 접두사 (선택)", placeholder="경주", key="t4_bp")

    st.divider()
    t4_mode = st.radio("경유지 입력 방식", ["📝 직접 입력", "📁 엑셀 파일"], horizontal=True, key="t4_mode")

    x_raw = ""
    x_prefix = ""

    if t4_mode == "📝 직접 입력":
        x_raw = st.text_area("🔀 경유지 X 목록 (한 줄에 하나씩)", placeholder="경주교육지원청\n경주시청\n경주경찰서", height=140, key="t4_x")
        x_prefix = st.text_input("경유지 지역 접두사 (선택)", placeholder="경주", key="t4_xp")
    else:
        src_t4 = st.radio("파일 소스", ["📁 data 폴더", "📤 직접 업로드"], horizontal=True, key="t4_src")
        xl_t4, file_src_t4 = None, None
        if src_t4 == "📁 data 폴더":
            local_files_t4 = [f for f in os.listdir(DATA_DIR) if f.endswith((".xlsx", ".xls"))]
            if local_files_t4:
                sel_t4 = st.selectbox("파일 선택", local_files_t4, key="t4_sel")
                file_src_t4 = os.path.join(DATA_DIR, sel_t4)
                xl_t4 = safe_excel_file(file_src_t4)
            else:
                st.warning("data/ 폴더에 엑셀 파일이 없습니다.")
        else:
            up_t4 = st.file_uploader("엑셀 업로드", type=["xlsx", "xls"], key="t4_up")
            if up_t4:
                file_src_t4 = up_t4
                xl_t4 = safe_excel_file(up_t4)

        if xl_t4:
            c1, c2 = st.columns(2)
            with c1: sheet_t4 = st.selectbox("시트", xl_t4.sheet_names, key="t4_sh")
            with c2: hrow_t4 = st.number_input("헤더 행", 1, value=1, key="t4_hr")
            df_t4 = safe_read_excel(file_src_t4, sheet_name=sheet_t4, header=int(hrow_t4) - 1)
            st.dataframe(df_t4.head(3), use_container_width=True)
            cols_t4 = list(df_t4.columns)
            x_col = st.selectbox("🔀 경유지 열", cols_t4, key="t4_xc")
            x_prefix = st.text_input("경유지 지역 접두사", placeholder="경주", key="t4_xp2")
            x_raw = "\n".join(df_t4[x_col].dropna().astype(str).tolist())
            st.caption(f"경유지 {len(df_t4[x_col].dropna())}곳 로드됨")

    if st.button("🚀 경유지별 소요시간 계산", type="primary", use_container_width=True, key="t4_btn",
                 disabled=not api_key or not a_loc or not b_loc or not x_raw.strip()):

        with st.spinner("출발지/도착지 조회 중..."):
            a_lng, a_lat, a_addr, a_matched = search_place(f"{a_prefix} {a_loc}".strip())
            if not a_lng:
                st.error("출발지(A)를 찾을 수 없습니다.")
                st.stop()
            b_lng, b_lat, b_addr, b_matched = search_place(f"{b_prefix} {b_loc}".strip())
            if not b_lng:
                st.error("도착지(B)를 찾을 수 없습니다.")
                st.stop()
            st.success(f"✅ A: {a_matched or a_loc} | B: {b_matched or b_loc}")

            direct_dist, direct_time, direct_err = get_route(a_lng, a_lat, b_lng, b_lat, priority)
            if direct_err:
                st.warning(f"⚠️ A→B 직행 경로 오류: {direct_err}")
                direct_time = None

        x_list = [x.strip() for x in x_raw.strip().splitlines() if x.strip()]
        st.info(f"경유지 {len(x_list)}곳 계산 중... (API 예상 소모: {len(x_list)*2+1}회)")

        results4 = []
        prog4 = st.progress(0, "계산 중...")

        for i, x_name in enumerate(x_list):
            q = f"{x_prefix} {x_name}".strip() if x_prefix else x_name
            x_lng, x_lat, x_addr, x_matched = search_place(q)
            time.sleep(0.1)

            if not x_lng:
                results4.append({
                    "경유지(X)": x_name,
                    "주소": "❌ 미발견",
                    "A→X 거리(km)": "-",
                    "A→X 시간(분)": "-",
                    "X→B 거리(km)": "-",
                    "X→B 시간(분)": "-",
                    "총 거리(km)": "-",
                    "총 시간(분)": "-",
                    "직행 대비 +분": "-",
                    "비고": "",
                    "_lng": None,
                    "_lat": None,
                })
                continue

            ax_dist, ax_time, ax_err = get_route(a_lng, a_lat, x_lng, x_lat, priority)
            time.sleep(0.15)
            xb_dist, xb_time, xb_err = get_route(x_lng, x_lat, b_lng, b_lat, priority)
            time.sleep(0.15)

            if ax_err or xb_err:
                ax_dist_fb = haversine(a_lng, a_lat, x_lng, x_lat)
                xb_dist_fb = haversine(x_lng, x_lat, b_lng, b_lat)
                total_dist = round(ax_dist_fb + xb_dist_fb, 1)
                total_time = None
                note = "직선거리"
            else:
                total_dist = round((ax_dist or 0) + (xb_dist or 0), 1)
                total_time = (ax_time or 0) + (xb_time or 0)
                note = ""

            if direct_time is not None and total_time is not None:
                extra = total_time - direct_time
                extra_str = f"+{extra}분" if extra > 0 else f"{extra}분"
            else:
                extra_str = "-"

            results4.append({
                "경유지(X)": x_name,
                "주소": x_addr or "",
                "A→X 거리(km)": ax_dist if ax_dist is not None else "-",
                "A→X 시간(분)": ax_time if ax_time is not None else "-",
                "X→B 거리(km)": xb_dist if xb_dist is not None else "-",
                "X→B 시간(분)": xb_time if xb_time is not None else "-",
                "총 거리(km)": total_dist if total_dist is not None else "-",
                "총 시간(분)": total_time if total_time is not None else "-",
                "직행 대비 +분": extra_str,
                "비고": note,
                "_lng": x_lng,
                "_lat": x_lat,
            })
            prog4.progress((i + 1) / len(x_list), f"{x_name} 완료...")

        prog4.empty()
        rdf4 = pd.DataFrame(results4)
        st.markdown("### 결과 요약")
        st.dataframe(rdf4[[c for c in rdf4.columns if not c.startswith("_")]], use_container_width=True)

        if HAS_FOLIUM and any(rdf4["_lng"].notna()):
            m4 = folium.Map(location=[rdf4["_lat"].mean(), rdf4["_lng"].mean()], zoom_start=12)
            folium.Marker([a_lat, a_lng], popup=f"A (근무지)<br>{a_matched or a_loc}",
                          icon=folium.Icon(color="red", icon="home")).add_to(m4)
            folium.Marker([b_lat, b_lng], popup=f"B (집)<br>{b_matched or b_loc}",
                          icon=folium.Icon(color="orange", icon="home")).add_to(m4)

            x_colors = ["blue", "green", "purple", "darkred", "cadetblue",
                        "darkblue", "pink", "gray", "lightred", "lightblue"]
            for idx, row in rdf4.iterrows():
                if pd.notna(row["_lng"]):
                    color = x_colors[idx % len(x_colors)]
                    popup = f"{row['경유지(X)']}<br>총 {row['총 시간(분)']}분"
                    folium.Marker([row["_lat"], row["_lng"]], popup=popup,
                                  icon=folium.Icon(color=color, icon="star")).add_to(m4)
                    folium.PolyLine([[a_lat, a_lng], [row["_lat"], row["_lng"]]],
                                    color=color, weight=2.5, opacity=0.6).add_to(m4)
                    folium.PolyLine([[row["_lat"], row["_lng"]], [b_lat, b_lng]],
                                    color=color, weight=2.5, opacity=0.6).add_to(m4)

            st_folium(m4, use_container_width=True, height=500, returned_objects=[], key="tab4_map")

        buf4 = BytesIO()
        out_df = rdf4[[c for c in rdf4.columns if not c.startswith("_")]]
        out_df.to_excel(buf4, index=False)
        buf4.seek(0)
        st.download_button("⬇️ 결과 엑셀 다운로드", buf4, "경유지비교_결과.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════
# TAB 5 : 수업나눔 일정 파서
# ═══════════════════════════════════════════════

def parse_subnanum_excel(file_src, sheet_name):
    """
    수업나눔 일정 엑셀 파서 (병합 셀 대응 + 데이터 시작행 자동 감지)
    ──────────────────────────────────────────────
    경북교육청 수업나눔 양식 구조 (0-indexed):
      행0 : 제목 (전체 병합)
      행1 : 주관청 (전체 병합)
      행2 : 그룹 헤더 → 순 / 지역 / 학교 / 교사 / 1학기 수업나눔...
      행3 : 세부 헤더 → (앞 4칸은 병합으로 비어있음) / 교과 / 차시 / 일시 / 장소 / 단원 / 학생수 / 수업주제
      행4~ : 실데이터 (첫 칸 = 순번 숫자)

    핵심: 행2(그룹헤더)와 행3(세부헤더)를 합쳐야 완전한 컬럼명이 됨.
          병합 셀로 인해 행3의 앞 칸들은 NaN → 행2 값을 사용.
    """
    raw = safe_read_excel(file_src, sheet_name=sheet_name, header=None)
    n_cols = raw.shape[1]

    # ── 1) 데이터 시작 행 자동 감지: 첫 열에 숫자 1이 처음 등장하는 행
    data_start_idx = None
    for i in range(len(raw)):
        if pd.to_numeric(raw.iloc[i, 0], errors="coerce") == 1:
            data_start_idx = i
            break
    if data_start_idx is None:
        raise ValueError("데이터 시작 행(순번 1)을 찾지 못했습니다. 파일 형식을 확인하세요.")

    # ── 2) 헤더 2개 행 결합 (병합 셀 복원)
    #   헤더는 data_start_idx 바로 앞 2행을 사용
    def _row_str(idx):
        if idx < 0:
            return pd.Series([""] * n_cols)
        return raw.iloc[idx].fillna("").astype(str)

    hrow_a = _row_str(data_start_idx - 2)  # 그룹 헤더 행
    hrow_b = _row_str(data_start_idx - 1)  # 세부 헤더 행

    seen = {}
    clean_headers = []
    for a, b in zip(hrow_a, hrow_b):
        a = a.strip().replace("\n", " ")
        b = b.strip().replace("\n", " ")
        # 세부 헤더(b)가 있으면 우선, 없으면 그룹 헤더(a) 사용
        h = b if (b and b != "nan") else a
        h = h if (h and h != "nan") else "열"
        seen[h] = seen.get(h, 0) + 1
        clean_headers.append(h if seen[h] == 1 else f"{h}_{seen[h]}")

    # ── 3) 데이터 추출
    data = raw.iloc[data_start_idx:].copy()
    data.columns = clean_headers
    data = data.dropna(how="all")
    num_col = clean_headers[0]
    data = data[pd.to_numeric(data[num_col], errors="coerce").notna()].reset_index(drop=True)

    return data, clean_headers, data_start_idx


with tab5:
    st.subheader("📋 수업나눔 일정 → 학교까지 거리 계산")
    st.caption(
        "경상북도교육지원청 양식의 '수업나눔 일정' 엑셀을 자동 파싱합니다. "
        "병합 셀 헤더 자동 인식 · openpyxl 오류 파일도 calamine 엔진으로 자동 전환."
    )

    # ── 파일 소스: data 폴더 우선, 업로드는 보조
    xl5, file_src5 = None, None
    lf5 = sorted([f for f in os.listdir(DATA_DIR) if f.endswith((".xlsx", ".xls"))])

    if lf5:
        # 수업나눔 관련 파일이 있으면 자동 선택
        default_idx = next(
            (i for i, f in enumerate(lf5) if "수업나눔" in f or "수업전문가" in f),
            0
        )
        col_f, col_u = st.columns([3, 2])
        with col_f:
            sel5 = st.selectbox("📁 data 폴더 파일 선택", lf5, index=default_idx, key="t5_sel")
            file_src5 = os.path.join(DATA_DIR, sel5)
        with col_u:
            st.markdown("<br>", unsafe_allow_html=True)
            up5 = st.file_uploader("또는 직접 업로드", type=["xlsx", "xls"], key="t5_up",
                                   label_visibility="collapsed")
            if up5:
                file_src5 = up5
    else:
        up5 = st.file_uploader("엑셀 업로드 (.xlsx / .xls)", type=["xlsx", "xls"], key="t5_up")
        if up5:
            file_src5 = up5
        else:
            st.warning("data/ 폴더에 엑셀 파일이 없습니다. 직접 업로드하세요.")

    if file_src5:
        try:
            xl5 = safe_excel_file(file_src5)
        except Exception as e:
            st.error(f"파일 열기 실패: {e}")

    if xl5:
        sheet5 = st.selectbox("시트 선택", xl5.sheet_names, key="t5_sh")

        # 원본 미리보기 (접이식)
        with st.expander("📄 원본 셀 미리보기 (상위 8행)", expanded=False):
            try:
                preview_raw = safe_read_excel(file_src5, sheet_name=sheet5, header=None)
                st.dataframe(preview_raw.head(8), use_container_width=True)
            except Exception as e:
                st.error(f"미리보기 오류: {e}")

        # 파싱 (자동 감지)
        try:
            df5, hdrs5, detected_row = parse_subnanum_excel(file_src5, sheet5)
            st.success(f"✅ 파싱 성공: {len(df5)}건 · 데이터 시작행 자동감지 = {detected_row + 1}행")
            st.dataframe(df5, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"파싱 실패: {e}")
            st.stop()

        st.divider()
        st.markdown("### 🚗 내 위치 → 수업 학교 거리 계산")

        cols5 = list(df5.columns)

        c1, c2, c3 = st.columns(3)
        with c1:
            school_col5 = st.selectbox("🏫 학교명 열", cols5,
                                        index=min(2, len(cols5)-1), key="t5_sc")
        with c2:
            time_col5 = st.selectbox("🕐 일시 열", cols5,
                                      index=min(6, len(cols5)-1), key="t5_tc")
        with c3:
            region5 = st.text_input("🗺️ 지역 접두사", value="경주", key="t5_rp")

        my_loc5 = st.text_input("🏠 내 출발 위치", placeholder="예: 경주 화천초등학교", key="t5_my")
        extra_cols5 = st.multiselect(
            "📎 결과에 포함할 추가 열",
            [c for c in cols5 if c not in [school_col5, time_col5]],
            key="t5_ec"
        )

        if st.button("🚀 거리 계산", type="primary", use_container_width=True, key="t5_btn",
                     disabled=not api_key or not my_loc5):

            with st.spinner("출발 위치 조회 중..."):
                my_lng5, my_lat5, my_addr5, _ = search_place(my_loc5)
                if not my_lng5:
                    my_lng5, my_lat5, my_addr5, _ = search_address(my_loc5)

            if not my_lng5:
                st.error("출발 위치를 찾을 수 없습니다.")
                st.stop()
            st.success(f"✅ 출발: **{my_addr5 or my_loc5}**")

            rows5 = df5[df5[school_col5].notna()].copy()
            total5 = len(rows5)
            results5 = []
            prog5 = st.progress(0, "계산 중...")
            dir_err_shown5 = False

            for i, (_, row) in enumerate(rows5.iterrows()):
                school = str(row[school_col5]).strip()
                q = f"{region5} {school}".strip() if region5 else school
                p_lng, p_lat, p_addr, matched = search_place(q)
                score = round(name_similarity(q, matched or ""), 2)
                time.sleep(0.1)

                dist_km, dur_min, note = None, None, ""
                if p_lng and score >= similarity_threshold:
                    dist_km, dur_min, err = get_route(my_lng5, my_lat5, p_lng, p_lat, priority)
                    time.sleep(0.15)
                    if err:
                        if not dir_err_shown5:
                            st.warning(f"⚠️ 길찾기 오류: {err} → 직선거리 대체")
                            dir_err_shown5 = True
                        dist_km = haversine(my_lng5, my_lat5, p_lng, p_lat)
                        note = "직선거리"
                elif p_lng:
                    matched = f"❌ 유사도 낮음 ({score:.0%})"
                    p_lng = p_lat = None
                else:
                    matched = "❌ 미발견"

                rec = {
                    "학교명": school,
                    "검색결과": matched or "❌",
                    "주소": p_addr or "",
                    "매칭점수": f"{score:.0%}",
                    "일시": row.get(time_col5, ""),
                    "거리(km)": dist_km if dist_km is not None else "-",
                    "소요시간(분)": dur_min if dur_min is not None else "-",
                    "비고": note,
                    "_lng": p_lng, "_lat": p_lat,
                }
                for c in extra_cols5:
                    rec[c] = row.get(c, "")
                results5.append(rec)
                prog5.progress((i+1)/total5, f"({i+1}/{total5}) {school}")

            prog5.empty()
            rdf5 = pd.DataFrame(results5)
            ok5 = rdf5[rdf5["거리(km)"] != "-"]

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("전체", f"{total5}곳")
            mc2.metric("성공", f"{len(ok5)}곳")
            mc3.metric("실패", f"{total5 - len(ok5)}곳")
            if len(ok5):
                mc4.metric("평균 거리", f"{ok5['거리(km)'].mean():.1f}km")

            sort5 = st.radio("정렬", ["거리(km)", "소요시간(분)", "일시"], horizontal=True, key="t5_sort")
            ok_s5 = ok5.copy()
            try:
                ok_s5 = ok_s5.sort_values(sort5)
            except Exception:
                pass
            disp5 = pd.concat([ok_s5, rdf5[rdf5["거리(km)"] == "-"]], ignore_index=True)
            show5 = [c for c in disp5.columns if not c.startswith("_")]

            def hl5(v):
                if v == "-": return "color:#aaa"
                try:
                    f = float(v)
                    return "color:#0a8a0a;font-weight:bold" if f <= 5 else ("color:#e67e00" if f <= 15 else "color:#cc3300")
                except Exception:
                    return ""

            try:
                styled5 = disp5[show5].style.map(hl5, subset=["거리(km)"])
            except Exception:
                styled5 = disp5[show5].style.applymap(hl5, subset=["거리(km)"])
            st.dataframe(styled5, use_container_width=True, hide_index=True)
            st.caption("🟢≤5km 🟠5~15km 🔴>15km | 직선거리: 길찾기 미응답 시 대체")

            # 지도
            if HAS_FOLIUM and ok5["_lng"].notna().any():
                st.subheader("🗺️ 지도")
                m5 = folium.Map(location=[my_lat5, my_lng5], zoom_start=11)
                folium.Marker([my_lat5, my_lng5], popup="출발지",
                              icon=folium.Icon(color="red", icon="home")).add_to(m5)
                for _, r in disp5.iterrows():
                    if r["_lat"]:
                        popup = f"{r['학교명']}<br>{r['거리(km)']}km / {r['소요시간(분)']}분"
                        folium.Marker([r["_lat"], r["_lng"]], popup=popup,
                                      icon=folium.Icon(color="blue", icon="info-sign")).add_to(m5)
                        folium.PolyLine([[my_lat5, my_lng5], [r["_lat"], r["_lng"]]],
                                        color="#3388ff", weight=1.5, opacity=0.5).add_to(m5)
                st_folium(m5, use_container_width=True, height=450, returned_objects=[], key="tab5_map")

            # 다운로드
            buf5 = BytesIO()
            disp5[show5].to_excel(buf5, index=False)
            buf5.seek(0)
            st.download_button("⬇️ 결과 엑셀 다운로드", buf5, "수업나눔_거리결과.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
