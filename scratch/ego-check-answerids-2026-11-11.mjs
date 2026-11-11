const task=await takeOverTaskSpace(2);const page=task.page("p1");
console.log(await page.evaluate(()=>[...document.querySelectorAll('input[type=checkbox]')].map(x=>({id:x.id,checked:x.checked,outer:x.outerHTML}))));
