const t=await claimTaskSpace(0); const p=t.page('p1');
await p.fill("input[placeholder='콘텐츠명으로 검색해 주세요.']", '성장');
await p.waitForTimeout(1800);
console.log((await p.snapshot()).slice(1000,5200));
