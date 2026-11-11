const t=await taskSpace(0); const p=t.page('p1');
await p.click('button:text-is("미리보기")');
console.log(await p.url());
console.log(await p.snapshot());
