const t=await claimTaskSpace(0); const p=t.page('p1');
await p.fill("input[placeholder='콘텐츠명으로 검색해 주세요.']", '발표');
await p.press("input[placeholder='콘텐츠명으로 검색해 주세요.']", 'Enter');
await p.waitForTimeout(1800);
const s=await p.snapshot(); const i=s.indexOf('콘텐츠 패널'); console.log(s.slice(i,i+4200));
