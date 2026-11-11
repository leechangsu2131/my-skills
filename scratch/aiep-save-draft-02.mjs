const t=await taskSpace(0); const p=t.page('p1');
await p.click("loc=role:button[name='임시저장']");
await p.waitForTimeout(1500);
console.log(await p.url());
console.log((await p.snapshot()).slice(-1600));
