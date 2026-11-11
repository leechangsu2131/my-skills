const task=await takeOverTaskSpace(2);const page=task.page("p1");
await page.click('details:nth-of-type(1) button.btn-delete');
await page.fill('textarea[placeholder="질문 생략 가능"]', "그림책은 글이 적어도 그림이 이야기의 중요한 정보를 전할 수 있다.");
await page.click('button.ox_answer_btn.o');
await page.click('.sticky.select-chip .chip-list button:nth-child(4)');
console.log(await page.snapshot({scope:"full_page"}));
