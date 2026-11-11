const task = await takeOverTaskSpace(2);
console.log({ tabs: await task.tabs() });
const page = task.page("p1");
console.log(await page.snapshot());
