const t=await taskSpace(0); const p=t.page('p1');
await p.click("button[aria-label='닫기']");
console.log((await p.snapshot()).slice(-900));
