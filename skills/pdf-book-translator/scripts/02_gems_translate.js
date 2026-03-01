/**
 * 02_gems_translate.js - Playwright로 Gemini Gems 자동 번역
 *
 * 사용법:
 *   node 02_gems_translate.js --chapter 1           # 챕터 1 번역
 *   node 02_gems_translate.js --chapter 1 --auth    # Google 로그인 세션 저장 (최초 1회)
 *
 * 실행 전 필요:
 *   npm install
 *   npx playwright install chromium
 */

const { chromium } = require("playwright-extra");
const stealth = require("puppeteer-extra-plugin-stealth")();
chromium.use(stealth);
const fs = require("fs");
const path = require("path");

// .env 파일 수동 로드 (dotenv 없이)
function loadEnv() {
  const envPath = path.join(__dirname, ".env");
  if (!fs.existsSync(envPath)) {
    console.error("❌ .env 파일이 없습니다. .env.example을 복사하고 설정하세요.");
    process.exit(1);
  }
  const lines = fs.readFileSync(envPath, "utf-8").split("\n");
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const [key, ...vals] = trimmed.split("=");
    process.env[key.trim()] = vals.join("=").trim();
  }
}

// 커맨드라인 인자 파싱
function parseArgs() {
  const args = { chapter: null, authOnly: false };
  for (let i = 2; i < process.argv.length; i++) {
    if (process.argv[i] === "--chapter" && process.argv[i + 1]) {
      args.chapter = parseInt(process.argv[i + 1]);
      i++;
    }
    if (process.argv[i] === "--auth") {
      args.authOnly = true;
    }
  }
  return args;
}

// toc.json 읽기
function loadToc() {
  const tocPath = path.join(__dirname, "toc.json");
  if (!fs.existsSync(tocPath)) {
    console.error("❌ toc.json이 없습니다. 먼저 01_setup_toc.py를 실행하세요.");
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(tocPath, "utf-8"));
}

// 챕터 텍스트 파일 읽기
function loadChapterText(chapterNum) {
  const txtPath = path.join(__dirname, "output", `chapter_${String(chapterNum).padStart(2, "0")}.txt`);
  if (!fs.existsSync(txtPath)) {
    console.error(`❌ 챕터 텍스트 파일이 없습니다: ${txtPath}`);
    console.error("   먼저 extract_chapter.py로 텍스트를 추출하세요.");
    process.exit(1);
  }
  return fs.readFileSync(txtPath, "utf-8");
}

// 번역 결과 저장
function saveTranslation(chapterNum, title, text) {
  const outputDir = path.join(__dirname, "output");
  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

  const outputPath = path.join(outputDir, `chapter_${String(chapterNum).padStart(2, "0")}_translated.txt`);
  const content = `[챕터 ${chapterNum}] ${title}\n${"=".repeat(50)}\n\n${text}`;
  fs.writeFileSync(outputPath, content, "utf-8");
  console.log(`\n💾 번역 저장 완료: ${outputPath}`);
  return outputPath;
}

// auth 세션 경로
const SESSION_PATH = path.join(__dirname, "auth", "google_session.json");

async function saveGoogleSession() {
  const authDir = path.join(__dirname, "auth");
  const profilePath = path.join(authDir, "playwright_profile");
  if (!fs.existsSync(authDir)) fs.mkdirSync(authDir, { recursive: true });

  const sessionConfig = {
    type: "local_profile",
    userDataDir: profilePath
  };
  fs.writeFileSync(SESSION_PATH, JSON.stringify(sessionConfig, null, 2), "utf-8");

  console.log(`✅ 전용 브라우저 프로필 설정 완료!`);
  console.log(`   경로: ${profilePath}`);
  console.log(`\n이제 로그인용 창을 띄웁니다. 구글 로그인을 수동으로 1회 진행해주세요.`);

  const browser = await chromium.launchPersistentContext(profilePath, {
    headless: false,
    args: ["--start-maximized", "--disable-blink-features=AutomationControlled"],
    viewport: null,
  });
  const page = await browser.newPage();
  await page.goto("https://gemini.google.com");

  console.log("\n👉 [중요] 브라우저 창에서 로그인을 완전히 마치신 후, 브라우저 창을 닫아주세요.");
  console.log("   (닫힐 때까지 스크립트가 대기합니다)");

  // 사용자가 브라우저를 닫을 때까지 대기
  await new Promise(resolve => browser.on('close', resolve));

  console.log("\n✅ 세션 저장 완료! 이제 번역을 실행할 수 있습니다.");
  console.log(`   node 02_gems_translate.js --chapter 1`);
}

async function translateChapter(chapterNum, chapterTitle, chapterText, gemsUrl) {
  console.log(`\n🤖 Gems 번역 시작: 챕터 ${chapterNum} "${chapterTitle}"`);

  const hasSession = fs.existsSync(SESSION_PATH);
  if (!hasSession) {
    console.log("⚠️  로그인 세션이 없습니다. 먼저 --auth 옵션으로 로그인하세요.");
    process.exit(1);
  }

  const sessionConfig = JSON.parse(fs.readFileSync(SESSION_PATH, "utf-8"));
  const userDataDir = sessionConfig.userDataDir;

  if (!userDataDir) {
    console.error("❌ Chrome 프로필 경로가 없습니다. node 02_gems_translate.js --auth 를 먼저 실행하세요.");
    process.exit(1);
  }

  // Chrome 자동화 프로필 사용
  const browser = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    slowMo: 50,
    args: [
      "--start-maximized",
      "--disable-blink-features=AutomationControlled" // 자동화 탐지 우회
    ],
    viewport: null,
  });
  const page = await browser.newPage();

  try {
    // Gems 페이지로 이동
    console.log("   📡 Gems 페이지로 이동 중...");
    await page.goto(gemsUrl, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(2000);

    // 로그인 확인 - 로그인 페이지로 리다이렉트됐으면 세션 만료
    if (page.url().includes("accounts.google.com")) {
      console.error("❌ 세션이 만료되었습니다. --auth 옵션으로 다시 로그인하세요.");
      await browser.close();
      process.exit(1);
    }

    // 텍스트 인풋 찾기 (Gemini 채팅창)
    console.log("   🔍 채팅 입력창 탐색 중...");
    const inputSelectors = [
      'div[contenteditable="true"]',
      'textarea[placeholder*="메시지"]',
      'textarea[placeholder*="Message"]',
      '[aria-label*="메시지"]',
      '[aria-label*="message"]',
      'rich-textarea',
    ];

    let inputEl = null;
    for (const sel of inputSelectors) {
      inputEl = page.locator(sel).first();
      if (await inputEl.isVisible({ timeout: 3000 }).catch(() => false)) {
        console.log(`   ✅ 입력창 발견: ${sel}`);
        break;
      }
      inputEl = null;
    }

    if (!inputEl) {
      throw new Error("채팅 입력창을 찾을 수 없습니다. Gems 페이지 구조가 변경되었을 수 있습니다.");
    }

    // 챕터 텍스트 입력 (긴 텍스트는 클립보드로 붙여넣기)
    console.log("   ✍️  챕터 텍스트 입력 중...");
    await inputEl.click();

    // 텍스트가 길면 클립보드 방식 사용
    await page.evaluate((text) => {
      const dataTransfer = new DataTransfer();
      dataTransfer.setData("text/plain", text);
      const el = document.querySelector('div[contenteditable="true"], rich-textarea');
      if (el) {
        el.focus();
        document.execCommand("insertText", false, text);
      }
    }, chapterText.slice(0, 8000)); // Gems 입력 한도 고려

    await page.waitForTimeout(1000);

    // 전송 버튼 클릭
    console.log("   📤 번역 요청 전송 중...");
    const sendSelectors = [
      'button[aria-label*="전송"]',
      'button[aria-label*="Send"]',
      'button[data-test-id*="send"]',
      '[aria-label="메시지 보내기"]',
    ];

    let sent = false;
    for (const sel of sendSelectors) {
      const btn = page.locator(sel).first();
      if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await btn.click();
        sent = true;
        console.log(`   ✅ 전송 완료 (${sel})`);
        break;
      }
    }

    // 전송 버튼 못 찾으면 Enter로 전송
    if (!sent) {
      await inputEl.press("Enter");
      console.log("   ✅ Enter로 전송");
    }

    // 응답 대기 (로딩 인디케이터 사라질 때까지)
    console.log("   ⏳ 번역 결과 대기 중... (최대 2분)");
    await page.waitForTimeout(3000);

    // 응답 완료 감지: 로딩 스피너가 사라지거나 새 메시지 블록 등장
    await page.waitForFunction(() => {
      // Gemini UI에서 로딩 중 표시가 없어질 때까지 대기
      const loadingEls = document.querySelectorAll(
        '[aria-label*="로딩"], [aria-label*="Loading"], .loading-indicator, [data-test-id*="loading"]'
      );
      return loadingEls.length === 0;
    }, { timeout: 120000 }).catch(() => {
      console.log("   ⚠️  로딩 감지 실패, 30초 추가 대기...");
    });

    await page.waitForTimeout(5000); // 추가 안정 대기

    // 최신 응답 텍스트 추출
    console.log("   📋 번역 결과 추출 중...");
    const responseSelectors = [
      "model-response",
      ".model-response-text",
      '[data-testid="response"]',
      ".response-container p",
      "message-content",
      ".markdown",
    ];

    let translatedText = "";
    for (const sel of responseSelectors) {
      const els = await page.locator(sel).all();
      if (els.length > 0) {
        // 마지막(최신) 응답 블록 가져오기
        const lastEl = els[els.length - 1];
        const text = await lastEl.innerText().catch(() => "");
        if (text.length > 50) {
          translatedText = text;
          console.log(`   ✅ 응답 추출 완료 (${sel}) - ${text.length}자`);
          break;
        }
      }
    }

    if (!translatedText) {
      // 폴백: 전체 페이지에서 최신 텍스트 블록 찾기
      translatedText = await page.evaluate(() => {
        const allResponses = document.querySelectorAll("[data-message-author-role='model'], .model-turn");
        if (allResponses.length === 0) return "";
        const last = allResponses[allResponses.length - 1];
        return last ? last.innerText : "";
      });
    }

    if (!translatedText) {
      throw new Error("번역 결과를 추출하지 못했습니다. 페이지 구조를 확인하세요.");
    }

    await browser.close();
    return translatedText;

  } catch (err) {
    await page.screenshot({ path: path.join(__dirname, "output", "error_screenshot.png") });
    console.error(`\n❌ 오류 발생: ${err.message}`);
    console.error("   오류 스크린샷: output/error_screenshot.png");
    await browser.close();
    throw err;
  }
}

async function main() {
  loadEnv();
  const args = parseArgs();

  const gemsUrl = process.env.GEMS_URL;
  if (!gemsUrl) {
    console.error("❌ GEMS_URL이 .env에 설정되지 않았습니다.");
    process.exit(1);
  }

  // 인증 전용 모드
  if (args.authOnly) {
    await saveGoogleSession();
    console.log("\n✅ 이제 --auth 없이 번역을 실행할 수 있습니다.");
    console.log("   예: node 02_gems_translate.js --chapter 1");
    return;
  }

  if (!args.chapter) {
    console.error("❌ 챕터 번호를 지정하세요. 예: node 02_gems_translate.js --chapter 1");
    process.exit(1);
  }

  // 목차에서 챕터 정보 가져오기
  const toc = loadToc();
  const chapter = toc.find((c) => c.chapter === args.chapter);
  if (!chapter) {
    console.error(`❌ 챕터 ${args.chapter}을 toc.json에서 찾을 수 없습니다.`);
    console.error("   현재 목차:", toc.map((c) => `${c.chapter}장 "${c.title}"`).join(", "));
    process.exit(1);
  }

  // 챕터 텍스트 로드
  const chapterText = loadChapterText(args.chapter);
  console.log(`\n📖 챕터 ${args.chapter}: "${chapter.title}" (${chapterText.length}자)`);

  // Gems로 번역
  const translated = await translateChapter(args.chapter, chapter.title, chapterText, gemsUrl);

  // 결과 저장
  const outputPath = saveTranslation(args.chapter, chapter.title, translated);
  console.log(`\n✅ 완료! 번역 결과: ${outputPath}`);
}

main().catch((err) => {
  console.error("\n❌ 실행 오류:", err.message);
  process.exit(1);
});
