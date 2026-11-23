import json
import subprocess

handles = [660280, 2692258, 3609124, 10884502, 1774036, 659038, 1249076, 2952876, 332296, 397824]
# user32 GetWindowText
import ctypes
user32 = ctypes.windll.user32

for h in handles:
    length = user32.GetWindowTextLengthW(h)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(h, buff, length + 1)
    is_vis = user32.IsWindowVisible(h)
    print(f"HWND: {h} | Visible: {is_vis} | Title: {buff.value}")
