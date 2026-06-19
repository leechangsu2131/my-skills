import asyncio
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright

def _load_password() -> str:
    own_env = Path(__file__).parent.parent / ".env"
    if own_env.exists():
        from dotenv import load_dotenv
        load_dotenv(own_env, override=True)
    return os.environ.get("ISCREAM_EVAL_PASSWORD", "dlckdtn3")

async def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
            
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            print("Connected to Chrome!")
        except Exception as e:
            print(f"Connection failed: {e}")
            return
            
        page = None
        for ctx in browser.contexts:
            for pg in ctx.pages:
                if "i-scream" in pg.url:
                    page = pg
                    break
        if not page:
            print("i-scream page not found")
            return
            
        await page.bring_to_front()
        
        # Navigate to subject evaluation page
        print("Navigating to Evaluation page...")
        await page.goto("https://www.i-scream.co.kr/user/subjectevaluation/SubjectEvaluation.do", timeout=15000)
        await page.wait_for_timeout(3000) # Wait for page load
        
        # Check if password page is showing
        password_frame = None
        for frame in [page] + page.frames:
            try:
                if await frame.locator("input#psw").count() > 0:
                    password_frame = frame
                    break
            except Exception:
                continue
                
        if password_frame:
            print("Password check detected. Entering password...")
            pwd = _load_password()
            await password_frame.locator("input#psw").fill(pwd)
            await page.wait_for_timeout(500)
            
            # Click confirm button
            confirm_clicked = False
            for btn_sel in ["a:has-text('확인')", "button:has-text('확인')", "a.cbtn_rtyp1", "text='확인'", "a[onclick*='fnSubmit']"]:
                try:
                    btn = password_frame.locator(btn_sel)
                    if await btn.count() > 0:
                        await btn.first.click(timeout=2000)
                        confirm_clicked = True
                        break
                except Exception:
                    continue
            await page.wait_for_timeout(4000)
            
        # Re-detect target frame after loading
        target_frame = page
        for frame in [page] + page.frames:
            try:
                if await frame.locator("tr[class^='exam-tr']").count() > 0:
                    target_frame = frame
                    break
            except Exception:
                continue

        # Force switch to "예시문 선택형" (important to render the result table)
        print("Switching generation type to '예시문 선택형'...")
        exam_radio = None
        for frame in [page] + page.frames:
            try:
                locator = frame.locator("input#rb-type-exam")
                if await locator.count() > 0:
                    exam_radio = locator
                    break
            except Exception:
                continue
        if exam_radio:
            await exam_radio.evaluate("el => { el.checked = true; el.click(); el.dispatchEvent(new Event('change', { bubbles: true })); }")
            await page.wait_for_timeout(3000) # Give it 3 seconds to fully load
            print("Switched successfully!")
        else:
            print("Could not find rb-type-exam radio button.")

        # Let's ensure the subject is Korean
        print("Selecting subject: 국어...")
        subject_radio = target_frame.locator('input[name="searchSubject"][value="국어"]').first
        if await subject_radio.count() > 0:
            await subject_radio.evaluate("el => el.click()")
            ok_btn = target_frame.locator("button.btn-ok[onclick*='fnSchFieldConfirm']").first
            if await ok_btn.count() > 0:
                await ok_btn.evaluate("el => el.click()")
            await page.wait_for_timeout(4000)

        # Now, check multiple students to see if evaluation is stored in textarea/buttons
        test_students = ["강시우", "오지윤", "최윤채"]
        print("\n=== FINAL VERIFICATION RESULTS FROM DATABASE ===")
        
        for student in test_students:
            print(f"Selecting student: {student}...")
            
            # Click on span.nm directly (same as working evaluate click)
            student_span = target_frame.locator(f'span.nm[title="{student}"]').first
            if await student_span.count() == 0:
                student_span = target_frame.locator(f'span.nm:text-is("{student}")').first
            
            if await student_span.count() > 0:
                # Force click on student span
                await student_span.evaluate("el => el.click()")
                await page.wait_for_timeout(2000) # Wait for details to render
                
                # Fetch textarea value of this student
                row_xpath = f'//tr[td[contains(@class, "wordwrap") and normalize-space(text())="{student}"]]'
                row_locator = target_frame.locator(row_xpath)
                
                val = await row_locator.evaluate("""el => {
                    const textarea = el.querySelector('textarea');
                    const button = el.querySelector('button.contentsBtn');
                    return {
                        textareaVal: textarea ? textarea.value : '',
                        buttonText: button ? button.innerText : ''
                    };
                }""")
                
                print(f"Student: {student}")
                print(f"  Saved Textarea: '{val['textareaVal']}'")
                print(f"  Saved Button Text: '{val['buttonText']}'")
                print("-" * 50)
            else:
                print(f"Student span for {student} not found on the page")

        # Capture final verification screen with selected student
        screenshot_path = r"C:\Users\user\.gemini\antigravity\brain\ddabe031-ed96-4d20-8981-abdbf7f6fff2\scratch\final_verification.png"
        await page.screenshot(path=screenshot_path)
        print(f"Final verification screenshot saved to: {screenshot_path}")

if __name__ == "__main__":
    asyncio.run(main())
