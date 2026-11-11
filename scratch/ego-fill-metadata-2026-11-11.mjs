const task = await takeOverTaskSpace(2);
const page = task.page("p1");
await page.fill('input[placeholder="제목을 입력해 주세요."]', "우리 반 그림책 작가 되기 | 12차시");
await page.click(77);
await page.click(42);
await page.click(45);
await page.click(63);
await page.fill("textarea", "그림책을 읽고 장면, 인물, 이야기 구조, 그림 재료를 탐색한 뒤 나만의 그림책을 창작하고 독자와 나누는 12차시 수업입니다. 3~6학년 공통안이며, 개인 경험을 공유하지 않아도 가상 인물이나 상상 이야기를 선택할 수 있습니다. 학생 작품의 공개와 사진 촬영은 별도 동의를 확인합니다.");
console.log(await page.snapshot());
