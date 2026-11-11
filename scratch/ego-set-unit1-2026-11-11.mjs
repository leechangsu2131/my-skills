const task=await takeOverTaskSpace(2);const page=task.page("p1");
await page.fill('input[placeholder="제목을 입력해 주세요."]', "그림책 창작 1~4차시 | 그림 읽기와 인물 탐색");
await page.fill("textarea", "전체 12차시 중 1~4차시 수업 자료입니다. 통그림책을 천천히 보고, 장면에서 떠오른 감각을 표현하며, 인물의 여러 면을 살펴봅니다. 3~6학년 공통안입니다. 개인 경험을 공개할 필요는 없으며, 가상 인물이나 상상 장면으로 참여해도 됩니다.");
await page.click('details:nth-of-type(4) button.btn-delete');
await page.click('.sticky.select-chip .chip-list button:nth-child(4)');
console.log(await page.snapshot({scope:"full_page"}));
