const task = await takeOverTaskSpace(2);
const page = task.page("p1");
console.log(await page.snapshot({ scope: "full_page" }));
