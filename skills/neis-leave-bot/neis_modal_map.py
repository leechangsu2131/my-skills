"""
나이스(NEIS) 신청 모달 정밀 분석 + 자동 입력 스크립트
=====================================================
- 이미 '신청' 모달이 열려있는 상태에서 실행합니다.
- JavaScript를 이용해 오직 화면에 보이는 요소만 추출합니다.
- 라벨과 입력칸의 관계를 시각적 위치 기반으로 매핑합니다.

사용법:
  1. neis_apply.py 로 '신청' 버튼 클릭 완료 상태
  2. 화면에 신청 모달이 열려있는 상태에서
  3. python neis_modal_map.py
"""

import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException

REMOTE_PORT = 9222


def attach():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    print(f"[✓] 연결 성공: {driver.title}")
    return driver


# ─────────────────────────────────────────────
# JavaScript로 보이는 입력칸만 추출 + 라벨 매핑
# ─────────────────────────────────────────────

JS_ANALYZE = """
(function() {
    var result = [];
    
    // 화면에 보이는 입력 요소만 (display:none 제외)
    var inputs = Array.from(document.querySelectorAll(
        'input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]), textarea, select'
    )).filter(function(el) {
        var style = window.getComputedStyle(el);
        var rect = el.getBoundingClientRect();
        return style.display !== 'none' 
            && style.visibility !== 'hidden' 
            && rect.width > 0 && rect.height > 0
            && rect.top >= 0 && rect.top < window.innerHeight;
    });
    
    inputs.forEach(function(el, idx) {
        // 근처 라벨 텍스트 찾기
        var labelText = '';
        
        // 1. for 속성 매핑
        if (el.id) {
            var lbl = document.querySelector('label[for="' + el.id + '"]');
            if (lbl) labelText = lbl.innerText.trim();
        }
        
        // 2. 부모/형제 td나 th에서 찾기
        if (!labelText) {
            var parent = el.parentElement;
            for (var i = 0; i < 4; i++) {
                if (!parent) break;
                var prevSib = parent.previousElementSibling;
                if (prevSib) {
                    var txt = prevSib.innerText.trim();
                    if (txt && txt.length < 30) { labelText = txt; break; }
                }
                parent = parent.parentElement;
            }
        }
        
        // 3. 부모 tr에서 첫번째 td/th 텍스트
        if (!labelText) {
            var tr = el.closest('tr');
            if (tr) {
                var firstCell = tr.querySelector('th, td');
                if (firstCell) labelText = firstCell.innerText.trim().split('\\n')[0];
            }
        }
        
        var rect = el.getBoundingClientRect();
        result.push({
            idx: idx,
            tag: el.tagName.toLowerCase(),
            type: el.type || el.tagName.toLowerCase(),
            id: el.id || '',
            name: el.name || '',
            value: el.value || '',
            label: labelText,
            top: Math.round(rect.top),
            left: Math.round(rect.left),
            options: el.tagName === 'SELECT' 
                ? Array.from(el.options).map(function(o){ return {val: o.value, txt: o.text.trim()}; })
                : []
        });
    });
    
    return JSON.stringify(result, null, 2);
})();
"""


def analyze_visible_fields(driver):
    """현재 화면에서 보이는 입력 필드를 JavaScript로 정밀 분석합니다."""
    print("\n[🔍 JavaScript 기반 정밀 분석 - 모든 iframe 탐색]")
    all_fields = []

    def run_js_in_current_frame(label):
        try:
            result_json = driver.execute_script(JS_ANALYZE)
            if result_json is None:
                return []  # JS 실행은 됐지만 반환값 없음 (빈 페이지 등)
            parsed = json.loads(result_json)
            if parsed:
                print(f"  → [{label}] {len(parsed)}개 발견")
            return [dict(f, frame_id=label) for f in parsed]
        except Exception as e:
            print(f"  → [{label}] JS 실행 오류: {e}")
            return []

    # 1. 메인 document
    driver.switch_to.default_content()
    all_fields += run_js_in_current_frame("main")

    # 2. 모든 iframe (2-depth 포함)
    try:
        driver.switch_to.default_content()
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"  iframe {len(iframes)}개 탐색 중...")
        for i, frame in enumerate(iframes):
            fid = frame.get_attribute("id") or frame.get_attribute("name") or f"#{i}"
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                all_fields += run_js_in_current_frame(f"iframe[{fid}]")

                # 중첩 iframe
                nested = driver.find_elements(By.TAG_NAME, "iframe")
                for j, nf in enumerate(nested):
                    nid = nf.get_attribute("id") or nf.get_attribute("name") or f"#{j}"
                    try:
                        driver.switch_to.frame(nf)
                        all_fields += run_js_in_current_frame(f"iframe[{fid}]>iframe[{nid}]")
                        driver.switch_to.parent_frame()
                    except Exception:
                        driver.switch_to.parent_frame()
            except Exception:
                pass
    finally:
        driver.switch_to.default_content()

    if not all_fields:
        print("  ✗ 보이는 입력칸을 찾지 못했습니다. 신청 모달이 열려있는지 확인하세요.")
        return []

    # idx 재부여 (frame 통합 후)
    for new_idx, f in enumerate(all_fields):
        f['global_idx'] = new_idx

    print(f"\n  ─ 최종 집계: {len(all_fields)}개 입력칸 ─")
    print(f"  {'#':>4}  {'frame':22}  {'라벨':20}  {'타입':12}  {'id':20}  값")
    print("  " + "-"*110)
    for f in all_fields:
        options_hint = f" [{', '.join(o['txt'] for o in f['options'][:4])}...]" if f['options'] else ""
        val_str = (f['value'] + options_hint)[:25]
        print(f"  [{f['global_idx']:>3}]  {f['frame_id']:22}  "
              f"{f['label'] or '(라벨없음)':20}  {f['type']:12}  "
              f"{f['id'] or '-':20}  {val_str}")

    return all_fields


# ─────────────────────────────────────────────
# 보이는 N번째 입력칸에 값 설정하기
# ─────────────────────────────────────────────

JS_SET_VISIBLE = """
(function(idx, value) {
    var inputs = Array.from(document.querySelectorAll(
        'input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]), textarea, select'
    )).filter(function(el) {
        var style = window.getComputedStyle(el);
        var rect = el.getBoundingClientRect();
        return style.display !== 'none' 
            && style.visibility !== 'hidden' 
            && rect.width > 0 && rect.height > 0
            && rect.top >= 0 && rect.top < window.innerHeight;
    });
    
    if (idx >= inputs.length) return 'ERROR: index out of range (' + inputs.length + ')';
    var el = inputs[idx];
    
    // React/Vue 등 프레임워크 대응: nativeInputValueSetter
    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype, 'value');
    if (nativeInputValueSetter && el.tagName === 'INPUT') {
        nativeInputValueSetter.set.call(el, value);
    } else {
        el.value = value;
    }
    
    // change / input 이벤트 발생 (프레임워크 반응 유도)
    ['input', 'change', 'blur'].forEach(function(evt) {
        el.dispatchEvent(new Event(evt, { bubbles: true }));
    });
    
    return 'OK: ' + el.tagName + '[' + idx + '] = ' + value;
})( arguments[0], arguments[1] );
"""


def set_field(driver, idx, value):
    """보이는 idx번째 필드에 값을 설정합니다."""
    r = driver.execute_script(JS_SET_VISIBLE, idx, value)
    print(f"  set_field({idx}, '{value}') → {r}")
    time.sleep(0.3)


def set_select(driver, idx, option_text):
    """보이는 idx번째 select 필드에서 텍스트로 옵션을 선택합니다."""
    js = """
    (function(idx, txt) {
        var inputs = Array.from(document.querySelectorAll(
            'input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]), textarea, select'
        )).filter(function(el) {
            var style = window.getComputedStyle(el);
            var rect = el.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' 
                && rect.width > 0 && rect.height > 0
                && rect.top >= 0 && rect.top < window.innerHeight;
        });
        if (idx >= inputs.length) return 'ERROR';
        var el = inputs[idx];
        var opts = Array.from(el.options);
        var found = opts.find(function(o){ return o.text.trim().includes(txt); });
        if (found) {
            el.value = found.value;
            el.dispatchEvent(new Event('change', {bubbles:true}));
            return 'OK: ' + found.text;
        }
        var available = opts.map(function(o){ return o.text.trim(); }).join(', ');
        return 'NOT_FOUND (사용가능: ' + available + ')';
    })(arguments[0], arguments[1]);
    """
    r = driver.execute_script(js, idx, option_text)
    print(f"  set_select({idx}, '{option_text}') → {r}")
    time.sleep(0.3)


# ─────────────────────────────────────────────
# 메인: 분석 실행
# ─────────────────────────────────────────────

def run():
    driver = attach()
    
    print("\n" + "="*55)
    print(" 보이는 입력 필드 정밀 분석")
    print("="*55)
    print("※ 신청 모달이 이미 열려있는 상태여야 합니다.")
    print("  (neis_apply.py 를 먼저 실행하거나 직접 신청 버튼을 누른 후 실행해주세요)\n")
    
    fields = analyze_visible_fields(driver)
    
    if fields:
        print("\n" + "="*55)
        print(" 💡 위 결과를 채팅창에 붙여넣어 주세요!")
        print(" idx 번호를 확인한 뒤 아래와 같이 자동 입력 가능합니다:")
        print("="*55)
        print("""
  # 예시 (idx 번호는 분석 결과에 따라 달라짐):
  set_select(driver, 0, "연가")    # 근무상황 드롭다운
  set_field(driver, 3, "2026-03-16")  # 시작일
  set_field(driver, 4, "2026-03-16")  # 종료일
  set_field(driver, 8, "개인 용무")   # 사유
""")


if __name__ == "__main__":
    run()
