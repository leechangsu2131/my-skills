const task = await claimTaskSpace(0);
const page = task.page('p1');
await page.fill("input[placeholder='파일의 제목을 입력해 주세요.']", '학생용 성장 발표회 준비 안내');
await page.fill("textarea[placeholder='설명을 입력해 주세요.']", '학생이 기억에 남는 성장 경험을 찾고, 이야기와 자료를 정리해 발표를 준비하는 안내 자료입니다. 실제 학생의 이름·사진·영상은 넣지 않았습니다.');
await page.click('text=비구매');
await page.click('text=제4유형 : 출처 표시 + 상업적 이용 금지 + 변경 금지');
console.log(await page.snapshot());
