(function () {
  "use strict";

  if (window.__NEIS_DUTY_HOOKED__) return;
  window.__NEIS_DUTY_HOOKED__ = true;

  const TARGET = "srv_mym_mm01_001.do";

  function toUrlText(input) {
    try {
      if (typeof input === "string") return input;
      if (input && typeof input.url === "string") return input.url;
    } catch (_) {}
    return "";
  }

  function isTarget(url) {
    return String(url || "").includes(TARGET);
  }

  function safePostMessage(payload) {
    try {
      window.postMessage({
        source: "NEIS_DUTY_HOOK",
        payload
      }, "*");
    } catch (_) {}
  }

  function dispatchRequest({ method, url, body, responseText }) {
    if (!isTarget(url)) return;
    safePostMessage({
      kind: "duty-api",
      method: method || "POST",
      url: String(url || ""),
      body: typeof body === "string" ? body : "",
      responseText: typeof responseText === "string" ? responseText : "",
      capturedAt: Date.now()
    });
  }

  // fetch 요청 감지
  const originalFetch = window.fetch;
  if (typeof originalFetch === "function") {
    window.fetch = async function patchedFetch(input, init) {
      const method = (init && init.method) || (input && input.method) || "GET";
      const url = toUrlText(input);
      const body = init && init.body;
      const response = await originalFetch.apply(this, arguments);

      if (isTarget(url)) {
        try {
          const clone = response.clone();
          clone.text().then((text) => {
            dispatchRequest({ method, url, body, responseText: text });
          }).catch(() => {
            dispatchRequest({ method, url, body, responseText: "" });
          });
        } catch (_) {
          dispatchRequest({ method, url, body, responseText: "" });
        }
      }
      return response;
    };
  }

  // XMLHttpRequest 요청 감지
  const xhrProto = window.XMLHttpRequest && window.XMLHttpRequest.prototype;
  if (xhrProto && xhrProto.open && xhrProto.send) {
    const originalOpen = xhrProto.open;
    const originalSend = xhrProto.send;

    xhrProto.open = function patchedOpen(method, url) {
      try {
        this.__jbeDutyMethod = method;
        this.__jbeDutyUrl = url;
      } catch (_) {}
      return originalOpen.apply(this, arguments);
    };

    xhrProto.send = function patchedSend(body) {
      try {
        const method = this.__jbeDutyMethod || "POST";
        const url = this.__jbeDutyUrl || "";
        if (isTarget(url)) {
          this.addEventListener("loadend", () => {
            let responseText = "";
            try {
              responseText = typeof this.responseText === "string" ? this.responseText : "";
            } catch (_) {}
            dispatchRequest({ method, url, body, responseText });
          });
        }
      } catch (_) {}
      return originalSend.apply(this, arguments);
    };
  }
})();
