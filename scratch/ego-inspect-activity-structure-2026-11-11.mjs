const task=await takeOverTaskSpace(2);const page=task.page("p1");
console.log(await page.evaluate(()=>[...document.querySelectorAll('button[aria-label="삭제"]')].map((e,i)=>{let a=[];for(let n=e,j=0;n&&j<5;n=n.parentElement,j++)a.push({tag:n.tagName,cls:n.className,text:(n.innerText||'').slice(0,60)});return {i,a}})));
