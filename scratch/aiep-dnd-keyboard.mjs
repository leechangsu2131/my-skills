const task = await claimTaskSpace(0);
const page = task.page('p1');
const src = '.drawer-item--file >> nth=1';
await page.focus(src);
await page.press(src, 'Space');
await page.press(src, 'ArrowRight');
console.log(await page.evaluate(() => document.querySelector('#DndLiveRegion-0')?.innerText));
console.log(await page.snapshot());
