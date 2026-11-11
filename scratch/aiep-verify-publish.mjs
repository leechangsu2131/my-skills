const t=await taskSpace(0); const p=t.page('p1');
await p.click('@399');
await p.click('loc=href:/course/list');
await p.waitForURL('**/course/list', {timeout:10000});
console.log(await p.url());
console.log(await p.snapshot());
