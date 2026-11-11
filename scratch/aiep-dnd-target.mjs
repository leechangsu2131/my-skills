const task = await claimTaskSpace(0);
const page = task.page('p1');
console.log(await page.evaluate(() => [...document.querySelectorAll('*')].filter(e => e.innerText?.trim() === '콘텐츠1').map(e => {
  const out=[]; let n=e;
  for(let i=0;n&&i<6;i++,n=n.parentElement){const r=n.getBoundingClientRect();out.push({tag:n.tagName,cls:n.className?.toString().slice(0,220),role:n.getAttribute('role'),aria:n.getAttribute('aria-roledescription'),text:n.innerText?.slice(0,180),rect:{x:r.x,y:r.y,w:r.width,h:r.height},html:n.outerHTML.slice(0,500)});}return out;
})));
