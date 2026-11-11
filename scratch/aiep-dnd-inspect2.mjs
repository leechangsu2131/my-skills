const task = await claimTaskSpace(0);
const page = task.page('p1');
console.log(await page.evaluate(() => ({
 dnd:[...document.querySelectorAll('[aria-roledescription]')].map(e=>({aria:e.getAttribute('aria-roledescription'),disabled:e.getAttribute('aria-disabled'),cls:e.className?.toString(),text:e.innerText?.slice(0,90),attrs:[...e.attributes].map(a=>[a.name,a.value]).filter(([n])=>n.startsWith('data-'))})),
 buttons:[...document.querySelectorAll('.bundle-card button')].map(e=>({label:e.getAttribute('aria-label'),title:e.title,cls:e.className,text:e.innerText,html:e.outerHTML.slice(0,400)}))
})));
