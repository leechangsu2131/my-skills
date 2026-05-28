#!/usr/bin/env python3
"""
체슬리모닝브리프 자동 요약 → Discord 전송
매일 오후 4시에 cron으로 실행됩니다.
"""

import json
import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date, timezone

# ─── 설정 ───────────────────────────────────────────────
CHANNEL_ID      = "UCXST0Hq6CAmG0dmo3jgrlEw"  # @chesleytv
KEYWORD         = "[체슬리모닝브리프]"
GEMINI_GEMS_URL = "https://gemini.google.com/gem/1R_gmS2NpyslXs0KJB6wpUjOuSad9TlVH"

# .env 파일에서 민감 정보 읽기
env_file = os.path.join(os.path.dirname(__file__), ".env")
DISCORD_WEBHOOK = ""
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            if line.startswith("DISCORD_WEBHOOK="):
                DISCORD_WEBHOOK = line.strip().split("=", 1)[1].strip('"').strip("'")

PROCESSED_FILE  = os.path.join(os.path.dirname(__file__), "processed.json")
RSS_URL         = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"

# ─── 처리된 영상 관리 ─────────────────────────────────────
def load_processed():
    try:
        with open(PROCESSED_FILE) as f:
            return json.load(f)
    except Exception:
        return []

def save_processed(processed):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)

# ─── YouTube RSS에서 오늘 영상 찾기 ──────────────────────
def get_todays_video():
    print(f"[1/5] YouTube RSS 확인 중... ({RSS_URL})")
    resp = requests.get(RSS_URL, timeout=15)
    resp.raise_for_status()

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt":   "http://www.youtube.com/xml/schemas/2015",
    }
    root = ET.fromstring(resp.content)
    today = date.today()

    for entry in root.findall("atom:entry", ns):
        title      = entry.find("atom:title", ns).text or ""
        published  = entry.find("atom:published", ns).text or ""
        video_id   = entry.find("yt:videoId", ns).text or ""

        pub_date = datetime.fromisoformat(published.replace("Z", "+00:00")).date()

        if KEYWORD in title and pub_date == today:
            url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"  → 발견: {title}")
            print(f"  → URL : {url}")
            return {"title": title, "video_id": video_id, "url": url}

    print("  → 오늘 날짜의 체슬리모닝브리프 영상이 없습니다.")
    return None

# ─── 스크립트(자막) 추출 ───────────────────────────────────
def get_transcript(video_id):
    print("[2/5] 유튜브 스크립트 추출 중...")
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        try:
            fetched = api.fetch(video_id, languages=["ko"])
        except Exception:
            fetched = api.fetch(video_id)

        text = " ".join(item.text for item in fetched)
        print(f"  → 스크립트 추출 완료 ({len(text):,}자)")
        return text

    except Exception as e:
        print(f"  → 스크립트 아직 없음: {e}")
        return None

# ─── Gemini Gems 브라우저 자동화 ──────────────────────────
def summarize_with_gemini_gems(transcript, video_title):
    print("[3/5] Gemini Gems에서 요약 생성 중... (브라우저 자동화)")

    prompt = f"""[긴급 지시사항: 절대 짧게 요약하지 마세요. 당신에게 설정된 '스크립트 정리 도우미'의 자체 지침(상세하게 구조화 등)을 100% 우선하여 적용하세요.]

다음은 유튜브 영상 "{video_title}"의 전체 스크립트입니다:

{transcript}"""  # 전체 스크립트 전송

    try:
        from patchright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=os.path.expanduser("~/.chesley-brief-browser"),
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = browser.new_page()

            # Gemini Gems 접속
            page.goto(GEMINI_GEMS_URL, timeout=30000)
            page.wait_for_timeout(3000)

            # 로그인 확인 (로그인 필요시 대기)
            if "signin" in page.url or "accounts.google" in page.url:
                print("  → Google 로그인 필요. 브라우저에서 로그인 후 Enter를 누르세요...")
                input()
                page.goto(GEMINI_GEMS_URL, timeout=30000)
                page.wait_for_timeout(3000)

            # 채팅 입력창 찾기
            selectors = [
                'rich-textarea[aria-label*="메시지"]',
                'rich-textarea',
                'div[contenteditable="true"]',
                'textarea',
            ]
            input_box = None
            for sel in selectors:
                try:
                    input_box = page.wait_for_selector(sel, timeout=5000)
                    if input_box:
                        break
                except Exception:
                    continue

            if not input_box:
                raise Exception("Gemini 입력창을 찾지 못했습니다.")

            # ── Pro 모드 선택 (빠른 모드 → Pro) ──────────────────
            try:
                # 모델 드롭다운 버튼 클릭 ("빠른 모드" 버튼)
                model_btn_selectors = [
                    'button:has-text("빠른 모드")',
                    'button:has-text("Flash")',
                    'button:has-text("Pro")',
                    '.model-selector button',
                    '[data-test-id="model-selector"]',
                ]
                model_btn = None
                for sel in model_btn_selectors:
                    try:
                        model_btn = page.query_selector(sel)
                        if model_btn:
                            break
                    except Exception:
                        continue

                if model_btn:
                    model_btn.click()
                    page.wait_for_timeout(1000)
                    # Pro 옵션 클릭
                    pro_selectors = [
                        'li:has-text("Pro")',
                        '[role="menuitem"]:has-text("Pro")',
                        'button:has-text("3.1 Pro")',
                        'div:has-text("3.1 Pro")',
                    ]
                    for sel in pro_selectors:
                        try:
                            pro_opt = page.query_selector(sel)
                            if pro_opt:
                                pro_opt.click()
                                page.wait_for_timeout(500)
                                print("  → Gemini 3.1 Pro 모드 선택 완료")
                                break
                        except Exception:
                            continue
                else:
                    print("  → 모델 드롭다운 미발견, 현재 모드로 진행")
            except Exception as e:
                print(f"  → Pro 모드 선택 오류 (무시하고 계속): {e}")

            # 프롬프트 입력 전 입력창 갱신 (Pro 모델 선택 후 DOM 변경 대비)
            input_box = None
            for sel in selectors:
                try:
                    input_box = page.wait_for_selector(sel, timeout=5000)
                    if input_box:
                        break
                except Exception:
                    continue

            if not input_box:
                raise Exception("Gemini 입력창을 다시 찾지 못했습니다.")

            input_box.click()
            page.wait_for_timeout(500)
            page.keyboard.press("Control+a")
            page.keyboard.press("Delete")
            page.wait_for_timeout(200)

            # 클립보드를 통해 붙여넣기 (한글 입력 문제 우회)
            page.evaluate(f"""
                navigator.clipboard.writeText({json.dumps(prompt)}).then(() => {{}});
            """)
            page.wait_for_timeout(500)
            page.keyboard.press("Control+v")
            page.wait_for_timeout(1000)
            page.keyboard.press("Space")
            page.wait_for_timeout(500)

            # 전송 (Enter 및 전송 버튼 클릭)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)
            
            # 전송 버튼을 찾아서 클릭 (엔터로 안 될 경우 대비)
            send_btn_selectors = [
                'button[aria-label*="전송"]',
                'button[aria-label*="Send"]',
                'button.send-button',
                '[data-test-id="send-button"]',
                '.bottom-bar button'
            ]
            for sel in send_btn_selectors:
                try:
                    btn = page.query_selector(sel)
                    if btn:
                        btn.click(timeout=1000)
                except Exception:
                    pass

            print("  → 프롬프트 전송 시도 완료. 응답 대기 중...")

            # 응답 완료 대기 (최대 120초)
            for i in range(120):
                page.wait_for_timeout(1000)
                # 로딩 중 아이콘 사라질 때까지 대기
                loading = page.query_selector('[aria-label*="중지"]') or \
                          page.query_selector('.loading') or \
                          page.query_selector('[data-is-loading="true"]')
                if not loading and i > 5:
                    break

            page.wait_for_timeout(2000)

            # 응답 텍스트 추출
            page.wait_for_timeout(2000)
            selectors_to_try = [
                'message-content', 
                'model-response', 
                '[data-message-author-role="model"]',
                '.model-response-text',
                '[data-test-id="message-content"]'
            ]
            
            response_els = []
            for sel in selectors_to_try:
                response_els = page.query_selector_all(sel)
                if response_els:
                    break
                    
            summary = ""
            if response_els:
                summary = response_els[-1].inner_text()
            else:
                # fallback: 전체 채팅 텍스트 중 마지막 프롬프트 이후 가져오기
                chat = page.query_selector('main, .chat-history, body')
                if chat:
                    all_text = chat.inner_text()
                    parts = all_text.split("전체 스크립트입니다:")
                    if len(parts) > 1:
                        summary = parts[-1]
                        # 입력했던 스크립트 텍스트 덩어리를 정확한 길이만큼 건너뛰기
                        prompt_len = len(prompt)
                        if len(summary) > prompt_len:
                            summary = summary[prompt_len:]
                        summary = summary.strip()

            if not summary or len(summary) < 50:
                print("  → [디버깅] 요약 추출 실패 또는 quá 짧음. 스크린샷 캡처 중...")
                page.screenshot(path="/Users/ichangsu/.gemini/antigravity/scratch/chesley-morning-brief/gemini_error.png", full_page=True)
                summary = ""

            browser.close()

            if summary:
                print(f"  → 요약 완료 ({len(summary):,}자)")
                return summary
            else:
                raise Exception("응답 텍스트 추출 실패")

    except Exception as e:
        print(f"  → Gemini Gems 오류: {e}")
        return None

# ─── Discord 전송 ──────────────────────────────────────────
def post_to_discord(summary, video):
    print("[4/5] Discord 전송 중...")
    today_str = date.today().strftime("%Y년 %m월 %d일")

    # Discord 메시지 최대 2000자 제한 처리 (Embed Description은 4096자까지 가능)
    max_len = 4000
    if len(summary) > max_len:
        summary_trimmed = summary[:max_len] + "\n...(이하 생략)"
    else:
        summary_trimmed = summary

    payload = {
        "embeds": [{
            "title": f"📰 {video['title']}",
            "description": summary_trimmed,
            "url": video["url"],
            "color": 0x5865F2,
            "footer": {"text": f"체슬리모닝브리프 자동요약 | {today_str}"},
            "fields": [
                {"name": "🔗 원본 영상", "value": video["url"], "inline": False}
            ]
        }]
    }

    resp = requests.post(DISCORD_WEBHOOK, json=payload, timeout=15)
    if resp.status_code in (200, 204):
        print("  → Discord 전송 성공!")
        return True
    else:
        print(f"  → Discord 전송 실패: {resp.status_code} {resp.text}")
        return False

# ─── 메인 ──────────────────────────────────────────────────
def main():
    print("=" * 50)
    print(f"체슬리모닝브리프 자동요약 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # 1. 오늘 영상 찾기
    video = get_todays_video()
    if not video:
        sys.exit(0)

    # 2. 이미 처리됐는지 확인
    processed = load_processed()
    if video["video_id"] in processed:
        print(f"  → 이미 처리된 영상입니다. 건너뜁니다.")
        sys.exit(0)

    # 3. 스크립트 추출
    transcript = get_transcript(video["video_id"])
    if not transcript:
        print("  스크립트가 아직 생성되지 않았습니다. 내일 다시 실행됩니다.")
        sys.exit(0)

    # 4. Gemini Gems로 요약
    summary = summarize_with_gemini_gems(transcript, video["title"])
    if not summary:
        print("  요약 생성 실패.")
        sys.exit(1)

    # 5. Discord 전송
    ok = post_to_discord(summary, video)
    if ok:
        processed.append(video["video_id"])
        save_processed(processed)
        print("\n[5/5] ✅ 완료!")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
