const task=await takeOverTaskSpace(2);const page=task.page("p1");
await page.fill('details:nth-of-type(2) input[placeholder="질문 생략 가능"]', "[1차시] 그림이 글과 함께 이야기를 전할 때, 어떤 단서를 살펴보면 좋을까요?");
await page.fill('details:nth-of-type(2) input[placeholder="보기1. 생략 가능"]', "글자의 개수만 세어 본다.");
await page.fill('details:nth-of-type(2) input[placeholder="보기2. 생략 가능"]', "색, 구도, 표정, 그림에만 보이는 정보를 살펴본다.");
await page.fill('details:nth-of-type(2) input[placeholder="보기3. 생략 가능"]', "등장인물 이름만 외운다.");
await page.fill('details:nth-of-type(2) input[placeholder="보기4. 생략 가능"]', "책의 크기만 비교한다.");
await page.click('#correctAnswer_1_1');
await page.click('.sticky.select-chip .chip-list button:nth-child(5)');
console.log(await page.snapshot({scope:"full_page"}));
