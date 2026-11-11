const task = await takeOverTaskSpace(2); const page=task.page("p1");
await page.click('.sticky.select-chip .chip-list button:nth-child(3)');
console.log(await page.snapshot({scope:"full_page"}));
