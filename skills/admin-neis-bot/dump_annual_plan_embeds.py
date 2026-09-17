#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
교과진도표관리 탭별 임베드앱 구조 심층 덤프
- tab1 안의 emb1~emb4 각각의 embeddedApp을 열어서 내부 컨트롤 출력
- 탭 클릭 후 각 임베드앱 ID 및 컨트롤 확인
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

for h in driver.window_handles:
    driver.switch_to.window(h)
    if "neis.go.kr" in driver.current_url:
        break

APP_ID = "edu/sw/els/edc/tm/els_edctm03_m00"

# ── 1. 탭폴더 탭 목록 + 임베드앱 ID 조회
print("=== [1] 탭폴더 탭 목록 & 임베드앱 ID ===")
tab_info = driver.execute_script("""
return (function(appId){
    try {
        var pl = cpr.core.Platform.INSTANCE;
        var inst = pl.getAllRunningAppInstances().find(function(ai){
            return ai && ai.app && ai.app.id === appId;
        });
        if (!inst) return {error:"앱 없음"};

        var container = inst.getContainer();
        var children = container.getAllRecursiveChildren();

        var result = {tabs:[], embeds:[]};

        children.forEach(function(c){
            if (!c) return;
            var type = c.type || "";
            var id   = c.id   || "";

            // 탭폴더 탭 정보
            if (type === "tabfolder" && id === "tab1") {
                try {
                    var tabItems = c.getTabItems ? c.getTabItems() : [];
                    tabItems.forEach(function(t, i){
                        result.tabs.push({
                            index: i,
                            text: t.text || t.label || "(no text)",
                            visible: t.visible,
                            value: t.value || ""
                        });
                    });
                } catch(e) { result.tabError = String(e); }
            }

            // embeddedapp
            if (type === "embeddedapp") {
                var embAppInst = null;
                try { embAppInst = c.getEmbeddedAppInstance ? c.getEmbeddedAppInstance() : null; } catch(e){}
                result.embeds.push({
                    id: id,
                    embAppId: embAppInst && embAppInst.app ? embAppInst.app.id : "(없음)"
                });
            }
        });

        return {ok:true, result:result};
    } catch(e){ return {error:String(e)}; }
})(arguments[0]);
""", APP_ID)

if tab_info.get("error"):
    print("ERROR:", tab_info["error"])
    sys.exit(1)

ti = tab_info["result"]
print("탭 목록:")
for t in ti["tabs"]:
    print(f"  [{t['index']}] {t['text']}  visible={t['visible']}")
print("\n임베드앱 목록:")
for e in ti["embeds"]:
    print(f"  embId={e['id']:10s}  → embAppId={e['embAppId']}")

# ── 2. 각 임베드앱 내부 컨트롤 덤프
print("\n=== [2] 각 임베드앱 내부 컨트롤 ===")
emb_dump = driver.execute_script("""
return (function(appId){
    try {
        var pl = cpr.core.Platform.INSTANCE;
        var inst = pl.getAllRunningAppInstances().find(function(ai){
            return ai && ai.app && ai.app.id === appId;
        });
        if (!inst) return {error:"앱 없음"};

        var container = inst.getContainer();
        var children  = container.getAllRecursiveChildren();

        var results = [];

        children.forEach(function(c){
            if (!c || c.type !== "embeddedapp") return;
            var embId = c.id || "?";
            var embInst = null;
            try { embInst = c.getEmbeddedAppInstance ? c.getEmbeddedAppInstance() : null; } catch(e){}
            if (!embInst) return;

            var embAppId = embInst.app ? embInst.app.id : "?";
            var info = {embId: embId, embAppId: embAppId, buttons:[], combos:[], grids:[], datasets:[]};

            try {
                var embContainer = embInst.getContainer();
                var embChildren  = embContainer.getAllRecursiveChildren();

                embChildren.forEach(function(ec){
                    if (!ec) return;
                    var eid  = ec.id   || "";
                    var etype = ec.type || "";

                    if (etype === "button" || eid.indexOf("btn") === 0) {
                        info.buttons.push({
                            id: eid, value: ec.value || "",
                            enabled: (typeof ec.enabled === "boolean") ? ec.enabled : "?",
                            visible: (typeof ec.visible === "boolean") ? ec.visible : "?"
                        });
                    } else if (etype === "combo" || eid.toLowerCase().indexOf("cmb") >= 0) {
                        var items = [];
                        try { items = (ec.getItems?ec.getItems():[]).map(function(it){return {label:it.label,value:it.value};}); }catch(e){}
                        info.combos.push({
                            id: eid,
                            currentText: ec.getText ? ec.getText() : "",
                            currentValue: ec.getValue ? ec.getValue() : "",
                            items: items
                        });
                    } else if (etype === "grid" || eid.indexOf("grd") === 0) {
                        var rowCnt = 0;
                        try { rowCnt = ec.getDataset ? ec.getDataset().getRowCount() : 0; } catch(e){}
                        info.grids.push({id: eid, rowCount: rowCnt});
                    } else if (etype === "dataset" || (ec.getColumnCount && ec.getRowCount)) {
                        var cols = [];
                        try {
                            var cnt = ec.getColumnCount ? ec.getColumnCount() : 0;
                            for (var i=0; i<Math.min(cnt,15); i++) cols.push(ec.getColumnId(i));
                        } catch(e){}
                        info.datasets.push({id: eid, rowCount: ec.getRowCount ? ec.getRowCount() : "?", columns: cols});
                    }
                });
            } catch(e) { info.error = String(e); }

            results.push(info);
        });

        return {ok:true, results:results};
    } catch(e){ return {error:String(e)}; }
})(arguments[0]);
""", APP_ID)

if emb_dump.get("error"):
    print("ERROR:", emb_dump["error"])
else:
    for emb in emb_dump["results"]:
        print(f"\n{'─'*60}")
        print(f"  [embId={emb['embId']}]  embAppId={emb['embAppId']}")
        if emb.get("error"):
            print(f"  ERROR: {emb['error']}")
            continue

        if emb["buttons"]:
            print(f"  버튼({len(emb['buttons'])}개):")
            for b in emb["buttons"]:
                print(f"    id={b['id']:25s} value='{b['value']:20s}' en={b['enabled']} vis={b['visible']}")

        if emb["combos"]:
            print(f"  콤보({len(emb['combos'])}개):")
            for cb in emb["combos"]:
                print(f"    id={cb['id']:25s} 현재='{cb['currentText']}' ({len(cb['items'])}개)")
                for it in cb["items"][:15]:
                    print(f"        ▪ {it['label']}  (value={it['value']})")
                if len(cb["items"]) > 15:
                    print(f"        ... 이하 {len(cb['items'])-15}개 생략")

        if emb["grids"]:
            print(f"  그리드({len(emb['grids'])}개):")
            for g in emb["grids"]:
                print(f"    id={g['id']:25s} rowCount={g['rowCount']}")

        if emb["datasets"]:
            print(f"  데이터셋({len(emb['datasets'])}개):")
            for ds in emb["datasets"]:
                print(f"    id={ds['id']:25s} 행={ds['rowCount']}  컬럼={ds['columns']}")

out = "annual_plan_emb_dump.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump({"tab_info": tab_info, "emb_dump": emb_dump}, f, ensure_ascii=False, indent=2)
print(f"\n[저장] {out}")
print("=== 완료 ===")
