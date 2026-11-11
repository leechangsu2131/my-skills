const t=await taskSpace(0); const p=t.page('p1');
await p.evaluate(()=>{window.__preventNativeDrag=e=>{if(e.target.closest?.('.drawer-item--file')) e.preventDefault()}; document.addEventListener('dragstart',window.__preventNativeDrag,true); const s=document.querySelectorAll('.drawer-item--file')[0]; s.style.userSelect='none'; s.style.webkitUserSelect='none';});
await p.mouse.move(270,495);
await p.mouse.down({button:'left'});
await p.waitForTimeout(150);
for (const [x,y] of [[275,495],[290,490],[330,475],[390,450],[460,420],[530,390],[600,360],[660,340],[710,320],[730,320]]) { await p.mouse.move(x,y); await p.waitForTimeout(70); }
await p.mouse.up();
await p.evaluate(()=>document.removeEventListener('dragstart',window.__preventNativeDrag,true));
console.log(await p.evaluate(()=>({live:document.querySelector('#DndLiveRegion-0')?.innerText,content:[...document.querySelectorAll('.bundle-card__cell')].slice(0,4).map(e=>e.innerText.slice(0,90))})));
console.log((await p.snapshot()).slice(-2000));
