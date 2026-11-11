const task=await takeOverTaskSpace(2);const page=task.page("p1");
console.log({tabs:await task.tabs()});
console.log(await page.snapshot({scope:"full_page"}));
