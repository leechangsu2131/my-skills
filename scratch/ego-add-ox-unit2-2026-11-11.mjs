const task=await takeOverTaskSpace(2);const page=task.page("p1");
await page.click('#correctAnswer_3_0');
await page.click('.sticky.select-chip .chip-list button:nth-child(3)');
await page.fill('details:nth-of-type(5) textarea[placeholder="질문 생략 가능"]', "[5~6차시] 모둠 그림책을 함께 만들 때, 한 사람의 아이디어만 그대로 따라야 한다.");
await page.click('details:nth-of-type(5) button.ox_answer_btn.x');
await page.click('.sticky.select-chip .chip-list button:nth-child(4)');
console.log(await page.snapshot({scope:"full_page"}));
