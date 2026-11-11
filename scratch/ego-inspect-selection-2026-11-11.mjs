const task = await takeOverTaskSpace(2); const page = task.page("p1");
console.log(await page.evaluate(() => ({selected:[...document.querySelectorAll("button[aria-selected=true]")].map(x=>x.innerText),radio:[...document.querySelectorAll("input[type=radio]")].map(x=>({id:x.id,checked:x.checked,disabled:x.disabled}))})));
