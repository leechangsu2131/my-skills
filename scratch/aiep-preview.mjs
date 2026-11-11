const t=await taskSpace(0); const p=t.page('p1');
await p.click("loc=role:button[name*='미리보기']");
console.log(await p.url());
console.log(await p.snapshot());
