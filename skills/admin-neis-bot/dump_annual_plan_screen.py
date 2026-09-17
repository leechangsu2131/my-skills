#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
교과진도표관리 화면 (els_edctm03_m00) 구조 완전 덤프
- 현재 열린 앱의 모든 컨트롤(버튼/콤보/그리드) 출력
- 과목 콤보박스 아이템 목록 출력
- 버튼 목록 전체 출력
"""
import io, sys, json, time, os
os.environ["no_proxy"] = "localhost,127.0.0.1"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8","utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

opts = Options()
opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=opts)

# NEIS 탭으로 전환
for h in driver.window_handles:
    driver.switch_to.window(h)
    if "neis.go.kr" in driver.current_url:
        break

APP_ID = "edu/sw/els/edc/tm/els_edctm03_m00"
print(f"[대상 앱] {APP_ID}\n")

result = driver.execute_script("""
return (function(appId){
    try {
        var pl = cpr.core.Platform.INSTANCE;
        var inst = pl.getAllRunningAppInstances().find(function(ai){
            return ai && ai.app && ai.app.id === appId;
        });
        if (!inst) return {error: "앱 없음: "+appId};

        var info = {appId: appId, buttons:[], combos:[], grids:[], datasets:[], others:[]};

        var container = inst.getContainer();
        if (!container) return {error: "getContainer() 반환 null"};

        var children = container.getAllRecursiveChildren ? container.getAllRecursiveChildren() : [];
        children.forEach(function(c){
            if (!c) return;
            var id   = c.id   || "";
            var type = c.type || "";

            if (type === "button" || (id && id.indexOf("btn") === 0)) {
                info.buttons.push({
                    id: id, type: type,
                    value: c.value || "",
                    enabled: (typeof c.enabled === "boolean") ? c.enabled : "?",
                    visible: (typeof c.visible === "boolean") ? c.visible : "?"
                });
            } else if (type === "combo" || (id && id.toLowerCase().indexOf("cmb") >= 0)) {
                var items = [];
                try { items = (c.getItems ? c.getItems() : []).map(function(it){ return {label:it.label, value:it.value}; }); } catch(e){}
                info.combos.push({
                    id: id, type: type,
                    currentText: c.getText ? c.getText() : "",
                    currentValue: c.getValue ? c.getValue() : "",
                    itemCount: items.length,
                    items: items
                });
            } else if (type === "grid" || (id && id.indexOf("grd") === 0)) {
                info.grids.push({id: id, type: type});
            } else if (type === "dataset" || (c.getColumnCount && c.getRowCount)) {
                var cols = [];
                try {
                    var cnt = c.getColumnCount ? c.getColumnCount() : 0;
                    for (var i=0; i<Math.min(cnt,20); i++) cols.push(c.getColumnId(i));
                } catch(e){}
                info.datasets.push({id: id, rowCount: c.getRowCount ? c.getRowCount() : "?", columns: cols});
            } else if (id) {
                info.others.push({id: id, type: type});
            }
        });

        return {ok: true, info: info};
    } catch(e){ return {error: String(e)}; }
})(arguments[0]);
""", APP_ID)

if result.get("error"):
    print("ERROR:", result["error"])
    sys.exit(1)

info = result["info"]

print("=== 버튼 목록 ===")
for b in info["buttons"]:
    print(f"  id={b['id']:25s} value='{b['value']:20s}' enabled={b['enabled']} visible={b['visible']}")

print("\n=== 콤보박스 목록 ===")
for cb in info["combos"]:
    print(f"  id={cb['id']:25s} 현재='{cb['currentText']}' ({cb['itemCount']}개 아이템)")
    for it in cb["items"][:20]:
        print(f"      ▪ {it['label']}  (value={it['value']})")
    if cb["itemCount"] > 20:
        print(f"      ... 이하 {cb['itemCount']-20}개 생략")

print("\n=== 그리드 목록 ===")
for g in info["grids"]:
    print(f"  id={g['id']:25s} type={g['type']}")

print("\n=== 데이터셋 목록 ===")
for ds in info["datasets"]:
    print(f"  id={ds['id']:25s} 행수={ds['rowCount']}  컬럼={ds['columns']}")

print("\n=== 기타 컨트롤 (id 있는 것) ===")
for o in info["others"][:30]:
    print(f"  id={o['id']:25s} type={o['type']}")

# JSON 저장
out = f"annual_plan_screen_dump.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n[저장] {out}")
print("=== 완료 ===")
