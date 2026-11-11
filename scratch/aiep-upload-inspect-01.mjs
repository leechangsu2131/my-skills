const task = await claimTaskSpace(0);
const page = task.page('p1');
console.log(await page.evaluate(() => [...document.querySelectorAll('input, [role="radio"]')].map(x => ({tag:x.tagName, type:x.type, role:x.getAttribute('role'), text:x.closest('label')?.innerText || x.parentElement?.innerText, checked:x.checked, aria:x.getAttribute('aria-checked'), value:x.value})).filter(x => x.text || x.type === 'radio')));
