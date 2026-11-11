const task = await claimTaskSpace(0);
const page = task.page('p1');
console.log(await page.evaluate(() => [...document.querySelectorAll('[aria-live], [role="status"], [role="alert"]')].map(e=>({role:e.getAttribute('role'),live:e.getAttribute('aria-live'),text:e.innerText,html:e.outerHTML.slice(0,600)}))));
