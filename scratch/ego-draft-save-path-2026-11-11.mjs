const task=await takeOverTaskSpace(2);const page=task.page("p1");
console.log(await page.evaluate(()=>{const d=document.querySelector('.data-contents');return [...d.children].map((e,i)=>({i,tag:e.tagName,cls:e.className,text:e.innerText.slice(0,30)}))}));
