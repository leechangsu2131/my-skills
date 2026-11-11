const task = await claimTaskSpace(0);
const page = task.page('p1');
console.log(await page.evaluate(() => [[302,571],[155,571],[920,525],[900,520]].map(([x,y])=>{const e=document.elementFromPoint(x,y);return {x,y,tag:e?.tagName,cls:e?.className?.toString(),text:e?.innerText?.slice(0,90),parent:e?.parentElement?.className?.toString()}})));
