#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""교과 연간지도계획 메뉴 탐색 - 탭 자동 전환 버전"""
import io, sys, json, time, os
os.environ["no_proxy"] = "localhost,127.0.0.1"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8","utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

opts = Options()
opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=opts)

# ── 전체 탭 목록 출력 후 neis 탭으로 전환
print("=== 열린 탭 목록 ===")
for h in driver.window_handles:
    driver.switch_to.window(h)
    print(f"  [{h[:8]}] {driver.title!r:30s}  {driver.current_url}")

# neis.go.kr 탭 찾기
neis_handle = None
for h in driver.window_handles:
    driver.switch_to.window(h)
    if "neis.go.kr" in driver.current_url:
        neis_handle = h
        print(f"\n[✓] NEIS 탭 발견: {driver.current_url}")
        break

if not neis_handle:
    print("\n[✗] neis.go.kr 탭을 찾을 수 없습니다.")
    print("    나이스에 로그인된 탭이 열려 있는지 확인해주세요.")
    sys.exit(1)

driver.switch_to.window(neis_handle)
time.sleep(1)

# ── 1. cpr 확인
print("\n=== [1] cpr 플랫폼 확인 ===")
chk = driver.execute_script("""
    try {
        var pl = cpr.core.Platform.INSTANCE;
        var apps = pl.getAllRunningAppInstances();
        return {ok: true, appCount: apps.length,
                appIds: apps.map(function(ai){ return ai&&ai.app?ai.app.id:"(null)"; })};
    } catch(e) { return {error: String(e)}; }
""")
if chk.get("error"):
    print("ERROR:", chk["error"])
    print("→ 나이스 메인 화면이 완전히 로드됐는지 확인하세요.")
    sys.exit(1)

print(f"실행 앱 {chk['appCount']}개:")
for a in chk["appIds"]:
    print(f"  - {a}")

# ── 2. 메뉴 키워드 검색
print("\n=== [2] 메뉴 키워드 검색: 진도/연간/계획 ===")
result = driver.execute_script("""
return (function(){
    try {
        var pl = cpr.core.Platform.INSTANCE;
        var indexApp = pl.getAllRunningAppInstances().find(function(ai){
            return ai && ai.app && ai.app.id === "app/com/main/Index";
        });
        if (!indexApp) return {error:"app/com/main/Index 없음 - 나이스 메인화면인지 확인"};

        var keywords = ["진도","연간","계획"];
        var dsIds = ["dsAllMenu","dsAllMenuNew","dsAllMenuLocal"];
        var seen = {}, matches = [];

        function val(ds,r,cols){
            for(var i=0;i<cols.length;i++){
                try{ var v=ds.getValue(r,cols[i]); if(v!=null&&String(v)!="") return String(v); }catch(e){}
            }
            return "";
        }

        dsIds.forEach(function(dsId){
            var ds = indexApp.lookup(dsId);
            if(!ds||!ds.getRowCount) return;
            for(var r=0;r<ds.getRowCount();r++){
                var nm   = val(ds,r,["MENU_NM","menuNm"]);
                var path = val(ds,r,["menuNmDepth","pgePathNm","DESC","MENU_DESC"]);
                var hay  = (nm+" "+path).toLowerCase();
                var hit  = keywords.some(function(k){ return hay.indexOf(k)>=0; });
                if(!hit) continue;
                var mid  = val(ds,r,["MENU_ID","menuId","V_MENU_ID","vMenuId"]);
                var pid  = val(ds,r,["PGM_ID","pgeId","CALL_PAGE"]);
                var key  = nm+"|"+mid+"|"+pid;
                if(seen[key]) continue; seen[key]=true;
                matches.push({ds:dsId, nm:nm, path:path, menuId:mid, pageId:pid});
            }
        });
        return {ok:true, matches:matches};
    } catch(e){ return {error:String(e)}; }
})();
""")

if result.get("error"):
    print("ERROR:", result["error"])
else:
    print(f"검색 결과: {len(result['matches'])}건")
    for m in result["matches"]:
        print(f"  [{m['ds']}] 메뉴명: {m['nm']}")
        print(f"           경로: {m['path']}")
        print(f"           menuId={m['menuId']}  pageId={m['pageId']}")
        print()

# ── 3. '학급담임' 관련 메뉴 전체
print("=== [3] '학급담임' 관련 메뉴 전체 ===")
result2 = driver.execute_script("""
return (function(){
    try {
        var pl = cpr.core.Platform.INSTANCE;
        var indexApp = pl.getAllRunningAppInstances().find(function(ai){
            return ai && ai.app && ai.app.id === "app/com/main/Index";
        });
        if (!indexApp) return {error:"Index 앱 없음"};

        var dsIds = ["dsAllMenu","dsAllMenuNew","dsAllMenuLocal"];
        var seen = {}, matches = [];

        function val(ds,r,cols){
            for(var i=0;i<cols.length;i++){
                try{ var v=ds.getValue(r,cols[i]); if(v!=null&&String(v)!="") return String(v); }catch(e){}
            }
            return "";
        }

        dsIds.forEach(function(dsId){
            var ds = indexApp.lookup(dsId);
            if(!ds||!ds.getRowCount) return;
            for(var r=0;r<ds.getRowCount();r++){
                var nm   = val(ds,r,["MENU_NM","menuNm"]);
                var path = val(ds,r,["menuNmDepth","pgePathNm","DESC","MENU_DESC"]);
                var hay  = (nm+" "+path).toLowerCase();
                if(hay.indexOf("학급담임")<0) continue;
                var mid  = val(ds,r,["MENU_ID","menuId","V_MENU_ID","vMenuId"]);
                var pid  = val(ds,r,["PGM_ID","pgeId","CALL_PAGE"]);
                var key  = nm+"|"+mid+"|"+pid;
                if(seen[key]) continue; seen[key]=true;
                matches.push({ds:dsId, nm:nm, path:path, menuId:mid, pageId:pid});
            }
        });
        return {ok:true, matches:matches};
    } catch(e){ return {error:String(e)}; }
})();
""")

if result2.get("error"):
    print("ERROR:", result2["error"])
else:
    print(f"검색 결과: {len(result2['matches'])}건")
    for m in result2["matches"]:
        print(f"  [{m['ds']}] 메뉴명: {m['nm']}")
        print(f"           경로: {m['path']}")
        print(f"           menuId={m['menuId']}  pageId={m['pageId']}")
        print()

print("=== 탐색 완료 ===")
