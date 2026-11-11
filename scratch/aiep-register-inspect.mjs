const t=await taskSpace(0); const p=t.page('p1');
console.log(await p.evaluate(()=>[...document.querySelectorAll('button')].filter(e=>e.innerText?.includes('등록')).map(e=>({text:e.innerText,disabled:e.disabled,aria:e.getAttribute('aria-disabled'),cls:e.className,html:e.outerHTML.slice(0,600)}))));
