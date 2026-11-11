const task=await takeOverTaskSpace(2);const page=task.page("p1");
console.log(await page.evaluate(()=>{const d=[...document.querySelectorAll('details')].find(x=>x.innerText.startsWith('객관식'));return [...d.querySelectorAll('input')].map((e,i)=>({i,type:e.type,ph:e.placeholder,value:e.value,checked:e.checked,outer:e.outerHTML,parent:e.parentElement.outerHTML.slice(0,300)}))}));
