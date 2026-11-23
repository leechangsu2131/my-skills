import ctypes

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

def enum_windows_callback(hwnd, extra):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            # Get class name
            class_buff = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_buff, 256)
            cname = class_buff.value
            if any(k in title for k in ['나이스', 'NEIS', '이창수', 'Google', 'Chrome', '에듀파인', '학생', '성적']):
                print(f"HWND: {hwnd} | Class: {cname} | Title: {title}")
    return True

user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
