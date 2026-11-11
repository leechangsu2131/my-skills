const task = await claimTaskSpace(0);
const page = task.page('p1');
await page.fill("input[placeholder='파일의 제목을 입력해 주세요.']", '성장 발표회 발표 준비 활동지');
await page.fill("textarea[placeholder='설명을 입력해 주세요.']", '학생이 처음의 나부터 지금의 나까지 성장 이야기를 정리하고, 발표 방법과 연습 계획을 세우는 빈칸 활동지입니다. 개인 이름이나 실제 학생 작품은 미리 넣지 않았습니다.');
await page.click('text=비구매');
await page.mouse.move(598, 677);
await page.mouse.wheel(0, 430);
await page.click('text=제4유형 : 출처 표시 + 상업적 이용 금지 + 변경 금지');
console.log(await page.evaluate(() => [...document.querySelectorAll('input[type="radio"]')].map(x => ({label:x.parentElement?.innerText, checked:x.checked, value:x.value}))));
