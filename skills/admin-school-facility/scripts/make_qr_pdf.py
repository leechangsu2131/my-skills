#!/usr/bin/env python3
"""교실 문 앞에 붙일 QR 코드 인쇄용 PDF를 만든다. (A4 한 장에 6개: 방 이름 + QR + 사용법)
QR 주소 = (웹앱 주소)?mode=student&room=방이름[&c=학생코드]
사용법:
  python make_qr_pdf.py --url https://script.google.com/macros/s/.../exec --config config.json --out 빈교실_QR.pdf
  python make_qr_pdf.py --url ... --rooms "러닝허브1,플레이허브1" --code 학생코드 --out qr.pdf
주의: 학생 코드(--code)를 넣으면 QR에 코드가 함께 들어간다. 코드를 바꾸면 QR을 다시 인쇄해야 한다.
필요: pip install qrcode pillow
"""
import argparse, json, os, urllib.parse
import qrcode
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("--url", required=True, help="배포한 웹앱 주소 (…/exec)")
ap.add_argument("--rooms", default="", help="쉼표로 구분한 방 이름. 없으면 --config의 student_rooms")
ap.add_argument("--config", default=None)
ap.add_argument("--code", default="", help="스크립트 속성 STUDENT_CODE 값(선택)")
ap.add_argument("--out", default="빈교실_QR.pdf")
ap.add_argument("--title", default="빈 교실 사용 QR")
a = ap.parse_args()

rooms = [r.strip() for r in a.rooms.split(",") if r.strip()]
if not rooms and a.config:
    rooms = json.load(open(a.config, encoding="utf-8")).get("student_rooms", [])
assert rooms, "방 이름이 없습니다 (--rooms 또는 --config의 student_rooms)"

def font(size, bold=False):
    for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-%s.ttc" % ("Bold" if bold else "Regular"),
              "/usr/share/fonts/truetype/nanum/NanumGothic%s.ttf" % ("Bold" if bold else ""),
              "C:/Windows/Fonts/malgun%s.ttf" % ("bd" if bold else ""), "/System/Library/Fonts/AppleSDGothicNeo.ttc"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

W, H = 1654, 2339            # A4, 200dpi
COLS, ROWS = 2, 3
cw, ch = W // COLS, H // ROWS
pages = []
for i in range(0, len(rooms), COLS * ROWS):
    page = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(page)
    for j, room in enumerate(rooms[i:i + COLS * ROWS]):
        cx, cy = (j % COLS) * cw, (j // COLS) * ch
        link = a.url + "?" + urllib.parse.urlencode({k: v for k, v in (("mode", "student"), ("room", room), ("c", a.code)) if v})
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2); qr.add_data(link); qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((440, 440))
        d.rectangle([cx + 30, cy + 30, cx + cw - 30, cy + ch - 30], outline="#444", width=3)
        d.text((cx + cw // 2, cy + 95), room, font=font(60, True), fill="black", anchor="mm")
        d.text((cx + cw // 2, cy + 150), a.title, font=font(28), fill="#555", anchor="mm")
        page.paste(img, (cx + (cw - 440) // 2, cy + 185))
        d.text((cx + cw // 2, cy + 668), "① QR을 찍어요  ② 학급·번호(별명)를 써요", font=font(28), fill="black", anchor="mm")
        d.text((cx + cw // 2, cy + 708), "③ 사용 시작 → 다 쓰면 '다 썼어요'를 눌러요", font=font(28), fill="black", anchor="mm")
    pages.append(page)
pages[0].save(a.out, "PDF", resolution=200, save_all=True, append_images=pages[1:])
print("saved", a.out, "- 방", len(rooms), "개,", len(pages), "쪽")
