const t=await taskSpace(0); const p=t.page('p1');
console.log(await p.evaluate(()=>[...document.querySelectorAll('button.icon-slide-btn--next')].map((e,i)=>{const r=e.getBoundingClientRect();const s=getComputedStyle(e);return {i,rect:{x:r.x,y:r.y,w:r.width,h:r.height},display:s.display,visibility:s.visibility,disabled:e.disabled,html:e.outerHTML}})));
