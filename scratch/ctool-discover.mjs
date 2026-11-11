const task=await taskSpace('ClassTool courseware integration discovery');
const page=task.page('p1');
await page.goto('https://ctool.co.kr/class/myClassLibrary/create');
console.log({spaceId:task.spaceId,url:await page.url(),title:await page.title()});
console.log(await page.snapshot());
