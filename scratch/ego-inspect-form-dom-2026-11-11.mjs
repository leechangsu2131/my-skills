const task = await takeOverTaskSpace(2);
const page = task.page("p1");
console.log(await page.evaluate(() => ({
  inputs: [...document.querySelectorAll("input,textarea")].map((el, i) => ({ i, tag: el.tagName, type: el.type, name: el.name, placeholder: el.placeholder, value: el.value, outer: el.outerHTML.slice(0,300) })),
  buttons: [...document.querySelectorAll("button")].map((el,i) => ({i,text:el.innerText,cls:el.className,aria:el.getAttribute("aria-label"),outer:el.outerHTML.slice(0,300)}))
})));
