const task=await takeOverTaskSpace(2);const page=task.page("p1");
console.log({before:await page.evaluate(()=>({inputs:[...document.querySelectorAll('textarea')].map(x=>x.value),details:[...document.querySelectorAll('details')].map(d=>({title:d.querySelector('summary .title')?.innerText, text:[...d.querySelectorAll('textarea,input[type=text]')].map(x=>x.value).filter(Boolean)}))}))});
await page.click('.data-contents > div.align.center.mb48.mt24:nth-child(7) button.btn-gray');
console.log(await page.snapshot());
