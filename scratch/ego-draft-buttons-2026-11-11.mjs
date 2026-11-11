const task=await takeOverTaskSpace(2);const page=task.page("p1");
console.log(await page.evaluate(()=>[...document.querySelectorAll('button')].filter(x=>x.innerText.trim()==='임시 저장').map((e,i)=>{const a=[];for(let n=e,j=0;n&&j<5;n=n.parentElement,j++)a.push({tag:n.tagName,cls:n.className,id:n.id});return {i,a}})));
