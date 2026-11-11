const task = await takeOverTaskSpace(2); const page=task.page("p1");
console.log(await page.evaluate(() => {const e=[...document.querySelectorAll("button")].find(x=>x.innerText.trim()==="콘텐츠전송"); const a=[];for(let n=e,i=0;n&&i<7;n=n.parentElement,i++)a.push({tag:n.tagName,cls:n.className,id:n.id,html:n.outerHTML.slice(0,400)});return a;}));
