const task = await takeOverTaskSpace(2);
const page = task.page("p1");
console.log(await page.evaluate(() => { const e=[...document.querySelectorAll("button")].find(x=>x.innerText.trim()==="창의적 체험활동"); const a=[]; let n=e; for(let i=0;n&&i<6;i++,n=n.parentElement) a.push({tag:n.tagName,cls:n.className,id:n.id,role:n.getAttribute("role"),html:n.outerHTML.slice(0,500)}); return a; }));
