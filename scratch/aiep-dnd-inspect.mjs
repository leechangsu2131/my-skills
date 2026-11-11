const task = await claimTaskSpace(0);
const page = task.page('p1');
console.log(await page.evaluate(() => {
  const all = [...document.querySelectorAll('*')];
  const targets = ['학생용 성장 발표회 준비 안내', '드래그 앤 드롭으로 콘텐츠를 등록해 주세요'];
  return targets.map(t => {
    const el = all.find(e => e.children.length === 0 && e.textContent?.trim() === t);
    let n = el;
    const out = [];
    for (let i=0; n && i<5; i++, n=n.parentElement) {
      const r=n.getBoundingClientRect();
      out.push({tag:n.tagName, cls:n.className?.toString().slice(0,160), text:n.innerText?.slice(0,180), rect:{x:r.x,y:r.y,w:r.width,h:r.height}, draggable:n.draggable, html:n.outerHTML.slice(0,600)});
    }
    return out;
  });
}));
