const task=await takeOverTaskSpace(2);const page=task.page("p1");
await page.fill('details:nth-of-type(6) input[placeholder="질문 생략 가능"]', "[7~8차시] 끝 장면이 처음의 장면이나 문장을 다시 떠올리게 하며 이야기가 돌아오는 구조는 무엇인가요?");
await page.fill('details:nth-of-type(6) input[placeholder="보기1. 생략 가능"]', "순환 구조");
await page.fill('details:nth-of-type(6) input[placeholder="보기2. 생략 가능"]', "시간 순서 구조");
await page.fill('details:nth-of-type(6) input[placeholder="보기3. 생략 가능"]', "평행 구조");
await page.fill('details:nth-of-type(6) input[placeholder="보기4. 생략 가능"]', "이야기 속 이야기 구조");
await page.click('.sticky.select-chip .chip-list button:nth-child(5)');
await page.fill('details:nth-of-type(7) textarea[placeholder="질문 생략 가능"]', "[9차시] 6장면 스토리보드의 시작·가장 큰 변화·마지막 장면을 각각 한 문장으로 적어 보세요. 아직 정하지 못한 칸은 물음표로 남겨도 됩니다.");
console.log(await page.evaluate(()=>({details:[...document.querySelectorAll('details')].map(x=>x.querySelector('summary .title')?.innerText),answers:[...document.querySelectorAll('input[type=checkbox]')].map(x=>x.id)})));
