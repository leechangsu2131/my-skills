const task=await claimTaskSpace(0); const page=task.page('p1');
await page.evaluate(()=>{const e=document.querySelectorAll('.drawer-item--file')[1]; e.style.userSelect='none'; e.style.webkitUserSelect='none';});
await page.mouse.move(300,570);
await page.mouse.down({button:'left'});
await page.waitForTimeout(100);
for (const [x,y] of [[302,570],[305,570],[310,570],[330,570],[400,570],[500,565],[600,555],[700,545],[800,535],[900,525],[920,520]]) { await page.mouse.move(x,y); await page.waitForTimeout(60); }
await page.mouse.up();
console.log(await page.evaluate(()=>({live:document.querySelector('#DndLiveRegion-0')?.innerText, count:document.querySelectorAll('.drawer-item--file').length})));
console.log((await page.snapshot()).slice(-1700));
