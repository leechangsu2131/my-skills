/* Gemini 대화 내보내기 북마클릿 (personal-daily-intake)
   gemini.google.com 대화 화면에서 누르면 '다운로드' 폴더에
   1) gemini-YYYY-MM-DD-제목.json — 내가 쓴 말과 답을 차례대로 전부
   2) 하루기록-YYYY-MM-DD.md   — 마지막 답의 코드 상자가 하루 기록 정리본(--- date: …)이면 그것만
   을 받는다. intake.py 가 2)를 다운로드 폴더에서 찾아 inbox 로 옮긴다.
   긴 대화는 위쪽이 아직 안 불러와졌을 수 있으니 맨 위까지 올린 뒤 누른다.
   이 파일은 줄을 합쳐 javascript: 주소로 쓴다(python intake.py bookmarklet) — 그래서 // 주석은 쓰지 않는다. */
(function () {
  var pick = function (el, sels) {
    if (!el) { return ""; }
    for (var i = 0; i < sels.length; i++) {
      var f = el.querySelector(sels[i]);
      if (f && f.innerText.trim()) { return f.innerText.trim(); }
    }
    return el.innerText.trim();
  };
  var qs = Array.prototype.slice.call(document.querySelectorAll("user-query"));
  var rs = Array.prototype.slice.call(document.querySelectorAll("model-response"));
  if (!qs.length && !rs.length) {
    alert("Gemini 대화를 못 찾았어요. gemini.google.com 대화 화면에서 눌러 주세요(화면 모양이 바뀌었을 수도 있어요).");
    return;
  }
  var turns = [];
  for (var i = 0; i < Math.max(qs.length, rs.length); i++) {
    turns.push({
      user: pick(qs[i], [".query-text", ".user-query-container"]),
      model: pick(rs[i], ["message-content", ".markdown"])
    });
  }
  var now = new Date();
  var pad = function (n) { return (n < 10 ? "0" : "") + n; };
  var ymd = now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate());
  var title = document.title.replace(/\s*[-|]\s*Gemini.*$/i, "").trim() || "gemini";
  var safe = title.replace(/[\\/:*?"<>|#\s]+/g, "_").slice(0, 40);
  var save = function (name, text, type) {
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: type }));
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  };
  save("gemini-" + ymd + "-" + safe + ".json", JSON.stringify({
    source: "gemini", url: location.href, title: title, exported: now.toISOString(), turns: turns
  }, null, 1), "application/json");
  var md = "";
  var last = rs[rs.length - 1];
  if (last) {
    var codes = last.querySelectorAll("pre code, code-block code");
    for (var j = codes.length - 1; j >= 0 && !md; j--) {
      var t = codes[j].innerText.trim();
      if (/^---\s*\n\s*date:/.test(t)) { md = t + "\n"; }
    }
  }
  if (md) {
    var d = (md.match(/date:\s*(\d{4}-\d{2}-\d{2})/) || [0, ymd])[1];
    setTimeout(function () { save("하루기록-" + d + ".md", md, "text/markdown"); }, 400);
  }
  alert("내보냄: 대화 " + turns.length + "개" + (md ? " + 하루 기록 정리본" : " (하루 기록 정리본은 없음)"));
})();
