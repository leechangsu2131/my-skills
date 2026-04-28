"""카카오 API 실제 호출 테스트 (경주시)"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("KAKAO_API_KEY")
HEADERS = {"Authorization": f"KakaoAK {API_KEY}"}


def test_search(query):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    res = requests.get(url, headers=HEADERS, params={"query": query, "size": 1}, timeout=5)
    print(f"    HTTP {res.status_code} | {res.text[:200]}")
    data = res.json()
    docs = data.get("documents", [])
    if docs:
        d = docs[0]
        return float(d["x"]), float(d["y"]), d.get("place_name"), d.get("road_address_name") or d.get("address_name")
    return None, None, None, None


def test_directions(origin_lng, origin_lat, dest_lng, dest_lat):
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    params = {
        "origin": f"{origin_lng},{origin_lat}",
        "destination": f"{dest_lng},{dest_lat}",
        "priority": "RECOMMEND",
    }
    res = requests.get(url, headers=HEADERS, params=params, timeout=8)
    if res.status_code == 200:
        data = res.json()
        routes = data.get("routes", [])
        if routes and routes[0].get("result_code") == 0:
            summary = routes[0]["summary"]
            return round(summary["distance"] / 1000, 1), round(summary["duration"] / 60, 0)
    return None, None


# ── 테스트: 경주 황성공원 → 첨성대 ──
print("=" * 50)
print("[테스트 1] 출발지 검색: 경주 황성공원")
olng, olat, oname, oaddr = test_search("경주 황성공원")
print(f"  결과: {oname} | {oaddr} | 위도 {olat}, 경도 {olng}")

print("\n[테스트 2] 목적지 검색: 경주 첨성대")
dlng, dlat, dname, daddr = test_search("경주 첨성대")
print(f"  결과: {dname} | {daddr} | 위도 {dlat}, 경도 {dlng}")

if olng and dlng:
    print("\n[테스트 3] 길찾기 API")
    dist, dur = test_directions(olng, olat, dlng, dlat)
    if dist:
        print(f"  ✅ 성공: 거리 {dist}km, 소요시간 {int(dur)}분")
    else:
        print(f"  ❌ 길찾기 API 실패 (HTTP {requests.get('https://apis-navi.kakaomobility.com/v1/directions', headers=HEADERS, params={'origin': f'{olng},{olat}', 'destination': f'{dlng},{dlat}', 'priority': 'RECOMMEND'}).status_code})")
else:
    print("\n  ❌ 좌표 조회 실패로 길찾기 테스트 생략")

# ── 테스트: 서울 강남역 → 서울시청 (잘 되는지 비교) ──
print("\n" + "=" * 50)
print("[비교 테스트] 서울 강남역 → 서울시청")
slng, slat, sname, saddr = test_search("강남역")
elng, elat, ename, eaddr = test_search("서울시청")
print(f"  출발: {sname} | {saddr}")
print(f"  도착: {ename} | {eaddr}")
if slng and elng:
    dist, dur = test_directions(slng, slat, elng, elat)
    if dist:
        print(f"  ✅ 성공: 거리 {dist}km, 소요시간 {int(dur)}분")
    else:
        print("  ❌ 길찾기 API 실패")

print("\n" + "=" * 50)
print("[테스트 완료]")
