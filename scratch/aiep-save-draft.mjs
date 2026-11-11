const t=await claimTaskSpace(0); const p=t.page('p1');
await p.click("loc=role:button[name='임시저장']");
await p.waitForTimeout(1000);
console.log(await p.url());
console.log((await p.snapshot()).slice(-1200));
