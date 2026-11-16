import sys
import os
import io
import json
import base64
import ctypes
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Ensure Default desktop binding
hDesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
if hDesk:
    user32.SetThreadDesktop(hDesk)

from comtypes import GUID, POINTER
import comtypes.client
import win32gui, win32ui
from PIL import Image

def grab_window_print(hwnd):
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    # Try PW_RENDERFULLCONTENT (2), fallback to 0
    result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
    if not result:
        result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)
    return im, w, h

mod = comtypes.client.GetModule("UIAutomationCore.dll")
CUIAutomation = mod.CUIAutomation
IUIAutomation = mod.IUIAutomation
IUIAutomationValuePattern = mod.IUIAutomationValuePattern
UIA_ValuePatternId = 10002

uia = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)

def get_window_handle(window_ref):
    if isinstance(window_ref, int) and window_ref > 0:
        return window_ref
    if isinstance(window_ref, str) and window_ref.isdigit() and int(window_ref) > 0:
        return int(window_ref)
    
    found = []
    def enum_cb(hwnd, extra):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if "쪽지관리함" in buf.value:
                found.append(hwnd)
        return True
    
    EnumDesktopWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumDesktopWindows(hDesk, EnumDesktopWindowsProc(enum_cb), 0)
    if found:
        return found[0]
    return 0

def capture_window_state(hwnd, include_screenshot=False):
    if not hwnd or not user32.IsWindow(hwnd):
        hwnd = get_window_handle(None)
    
    if not hwnd:
        raise ValueError("쪽지관리함 창을 찾을 수 없습니다.")

    # Get body from ID 1022
    top_elem = uia.ElementFromHandle(hwnd)
    walker = uia.RawViewWalker

    body_text = ""
    def find_body(node, depth=0):
        nonlocal body_text
        if depth > 5 or body_text: return
        child = walker.GetFirstChildElement(node)
        while child:
            cid = child.CurrentAutomationId or ""
            if cid == "1022":
                try:
                    pPattern = child.GetCurrentPattern(UIA_ValuePatternId)
                    if pPattern:
                        val_pat = pPattern.QueryInterface(IUIAutomationValuePattern)
                        body_text = val_pat.CurrentValue or ""
                except Exception:
                    pass
                if not body_text:
                    body_text = child.CurrentName or ""
                return
            find_body(child, depth + 1)
            child = walker.GetNextSiblingElement(child)

    find_body(top_elem)

    # Selected row text: if empty body, fallback
    row_text = body_text if body_text else "선택된 쪽지"
    row_lines = [l.strip() for l in row_text.splitlines() if l.strip()]
    if not row_lines:
        row_lines = ["선택된 쪽지"]

    # Construct accessibility tree string matching capture_macro expectations
    tree_lines = [
        "0 창 쪽지관리함",
        "  7 창 UltariList",
        f"    8 창 {row_lines[0]}"
    ]
    for sub in row_lines[1:]:
        tree_lines.append(f"      {sub}")
    
    tree_lines.append("  14 창 UserNameList")
    
    # Body value: escape or single line
    clean_body = body_text.replace("\r\n", "\n").replace("\r", "\n")
    tree_lines.append(f"  21 편집 Value: {clean_body} ID: 1022")
    
    tree_str = "\n".join(tree_lines)
    focused_element = f"8 창 {row_lines[0]}"

    result = {
        "accessibility": {
            "tree": tree_str,
            "focused_element": focused_element
        },
        "screenshots": []
    }

    if include_screenshot:
        try:
            img, w, h = grab_window_print(hwnd)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=95)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            result["screenshots"].append({
                "url": f"data:image/jpeg;base64,{b64}",
                "width": w,
                "height": h
            })
        except Exception as e:
            sys.stderr.write(f"Screenshot grab failed: {e}\n")

    return result

KEY_MAP = {
    "Down": 0x28,
    "Up": 0x26,
    "Home": 0x24,
    "End": 0x23,
    "Page_Down": 0x22,
    "Page_Up": 0x21,
    "Return": 0x0D,
    "Enter": 0x0D,
    "Escape": 0x1B,
    "Space": 0x20,
    "Tab": 0x09
}

def force_foreground(hwnd):
    fg_hwnd = user32.GetForegroundWindow()
    if fg_hwnd != hwnd:
        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
        cur_thread = kernel32.GetCurrentThreadId()
        user32.AttachThreadInput(cur_thread, fg_thread, True)
        user32.ShowWindow(hwnd, 9) # SW_RESTORE
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(cur_thread, fg_thread, False)
        time.sleep(0.1)

def send_key(hwnd, key):
    vk = KEY_MAP.get(key) or KEY_MAP.get(key.capitalize()) or KEY_MAP.get(key.upper())
    if not vk:
        # Check case insensitive
        for k, v in KEY_MAP.items():
            if k.lower() == key.lower():
                vk = v
                break
    if not vk:
        raise ValueError(f"지원하지 않는 키: {key}")
    
    force_foreground(hwnd)

    # For Home key, always ensure mouse click on UltariListScrollView to guarantee focus
    if key.lower() == "home":
        try:
            click_element(hwnd, 8)
            time.sleep(0.2)
        except Exception:
            pass

    # Send actual keybd_event with extended key flag and scan code
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002
    
    flags = 0
    if vk in (0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28):
        flags |= KEYEVENTF_EXTENDEDKEY

    scan = user32.MapVirtualKeyW(vk, 0)
    user32.keybd_event(vk, scan, flags, 0)
    time.sleep(0.05)
    user32.keybd_event(vk, scan, flags | KEYEVENTF_KEYUP, 0)
    time.sleep(0.1)
    return True

def click_element(hwnd, element_index=8):
    force_foreground(hwnd)
    
    # Find UltariListScrollView rect
    list_hwnds = []
    def enum_click_cb(h, extra):
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, cls, 256)
        if cls.value == "UltariListScrollView":
            list_hwnds.append(h)
        return True

    EnumChildProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumChildWindows(hwnd, EnumChildProc(enum_click_cb), 0)
    target_hwnd = list_hwnds[0] if list_hwnds else hwnd

    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(target_hwnd, ctypes.byref(rect))
    
    # Click inside target via physical mouse cursor
    click_x = rect.left + 80
    click_y = rect.top + 30
    user32.SetCursorPos(click_x, click_y)
    time.sleep(0.05)
    
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.04)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.1)
    return True

def main():
    # Read commands from stdin as JSON lines:
    # {"cmd": "get_window_state", "window": ..., "include_screenshot": true, "id": 1}
    # {"cmd": "press_key", "window": ..., "key": "Down", "id": 2}
    # {"cmd": "click", "window": ..., "element_index": 8, "id": 3}
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            cmd = req.get("cmd")
            window = req.get("window")
            hwnd = get_window_handle(window)
            
            if cmd == "get_window_state":
                inc_scr = req.get("include_screenshot", False)
                res = capture_window_state(hwnd, include_screenshot=inc_scr)
                print(json.dumps({"id": req_id, "ok": True, "data": res}, ensure_ascii=False))
            elif cmd == "press_key":
                key = req.get("key")
                send_key(hwnd, key)
                print(json.dumps({"id": req_id, "ok": True}, ensure_ascii=False))
            elif cmd == "click":
                idx = req.get("element_index", 8)
                click_element(hwnd, idx)
                print(json.dumps({"id": req_id, "ok": True}, ensure_ascii=False))
            elif cmd == "ping":
                print(json.dumps({"id": req_id, "ok": True, "pong": True}))
            else:
                print(json.dumps({"id": req_id, "ok": False, "error": f"Unknown cmd: {cmd}"}))
        except Exception as e:
            print(json.dumps({"id": req_id, "ok": False, "error": str(e)}, ensure_ascii=False))
        sys.stdout.flush()

if __name__ == "__main__":
    main()
