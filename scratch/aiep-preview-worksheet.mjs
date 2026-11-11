const t=await taskSpace(0); const p=t.page('p1');
await p.click('@365');
await p.waitForTimeout(2500);
const s=await p.snapshot(); console.log(s.slice(s.lastIndexOf('container "페이지 경로"')));
