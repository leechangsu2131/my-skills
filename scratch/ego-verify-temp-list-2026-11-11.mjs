const task=await takeOverTaskSpace(2);const page=task.page("p1");
await page.goto("https://ctool.co.kr/class/myClassLibrary/temp");
console.log(await page.snapshot({scope:"full_page"}));
