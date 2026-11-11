const t=await taskSpace(0); const p=t.page('p1');
console.log(await p.evaluate(()=>[...document.querySelectorAll('li')].map((e,i)=>({i,cls:e.className,txt:e.innerText.slice(0,240),buttons:[...e.querySelectorAll('button')].map(b=>({text:b.innerText,disabled:b.disabled,aria:b.getAttribute('aria-label'),cls:b.className}))})).filter(x=>x.txt.includes('성취기준')||x.txt.includes('학생용'))));
