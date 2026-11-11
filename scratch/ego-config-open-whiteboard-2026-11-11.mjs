const task=await takeOverTaskSpace(2);const page=task.page("p1");
await page.fill('details:nth-of-type(3) textarea[placeholder="질문 생략 가능"]', "[2~3차시] 그림책에서 오래 보고 싶었던 장면을 하나 떠올려, 색·시선·여백이 주는 느낌을 한 단어나 짧은 문장으로 적어 보세요. 개인 경험 대신 가상 인물이나 상상 장면을 골라도 됩니다. 답을 발표할지는 스스로 선택합니다.");
await page.click('.sticky.select-chip .chip-list button:nth-child(6)');
console.log(await page.snapshot({scope:"full_page"}));
