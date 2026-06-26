#!/usr/bin/env python3
"""Diagnose and cautiously enter achievement-level records into NEIS."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any


REMOTE_PORT = 9222
webdriver = None
Options = None
By = None
Select = None

JS_VISIBLE_FIELDS = """
return (function() {
  function visible(el) {
    var style = window.getComputedStyle(el);
    var rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' &&
      rect.width > 0 && rect.height > 0;
  }
  function labelFor(el) {
    if (el.id) {
      var lbl = document.querySelector('label[for="' + el.id + '"]');
      if (lbl) return lbl.innerText.trim();
    }
    var tr = el.closest('tr');
    if (tr) {
      var cell = tr.querySelector('th,td');
      if (cell) return cell.innerText.trim().split('\\n')[0];
    }
    return '';
  }
  var q = 'input:not([type=hidden]), textarea, select, button, a';
  return Array.from(document.querySelectorAll(q)).filter(visible).map(function(el, idx) {
    var rect = el.getBoundingClientRect();
    return {
      idx: idx,
      tag: el.tagName.toLowerCase(),
      type: el.type || '',
      id: el.id || '',
      name: el.name || '',
      text: (el.innerText || el.value || '').trim().slice(0, 120),
      label: labelFor(el).slice(0, 120),
      top: Math.round(rect.top),
      left: Math.round(rect.left),
      selector_hint: el.id ? ('#' + CSS.escape(el.id)) : (el.name ? (el.tagName.toLowerCase() + '[name="' + el.name + '"]') : '')
    };
  });
})();
"""


def attach(port: int = REMOTE_PORT):
    ensure_selenium()
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{port}")
    driver = webdriver.Chrome(options=opts)
    print(f"[connect] {driver.title}")
    return driver


def ensure_selenium() -> None:
    global webdriver, Options, By, Select
    if webdriver is not None:
        return
    try:
        from selenium import webdriver as selenium_webdriver
        from selenium.webdriver.chrome.options import Options as SeleniumOptions
        from selenium.webdriver.common.by import By as SeleniumBy
        from selenium.webdriver.support.ui import Select as SeleniumSelect
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "selenium is required for NEIS browser diagnosis/apply. "
            "Install it in this environment with: pip install selenium"
        ) from exc
    webdriver = selenium_webdriver
    Options = SeleniumOptions
    By = SeleniumBy
    Select = SeleniumSelect


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def record_summary(records: list[dict[str, Any]]) -> None:
    print(f"records: {len(records)}")
    print(f"students: {len({r.get('student') for r in records})}")
    print(f"inferred: {sum(1 for r in records if r.get('inferred'))}")
    for subject, count in sorted(Counter(r.get("subject", "") for r in records).items()):
        print(f"  - {subject}: {count}")


def diagnose(driver, dump: Path | None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    def collect(label: str) -> None:
        try:
            fields = driver.execute_script(JS_VISIBLE_FIELDS)
        except Exception as exc:
            print(f"[diagnose] {label}: {exc}")
            return
        for field in fields:
            field["frame"] = label
            results.append(field)
        if fields:
            print(f"[diagnose] {label}: {len(fields)} visible elements")

    driver.switch_to.default_content()
    collect("main")
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for i, frame in enumerate(frames):
        frame_id = frame.get_attribute("id") or frame.get_attribute("name") or f"#{i}"
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
            collect(f"iframe[{frame_id}]")
        except Exception as exc:
            print(f"[diagnose] iframe[{frame_id}]: {exc}")
    driver.switch_to.default_content()

    if dump:
        dump.parent.mkdir(parents=True, exist_ok=True)
        dump.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[diagnose] wrote {dump}")
    else:
        for field in results[:80]:
            print(
                f"[{field['frame']}] {field['tag']} id={field['id'] or '-'} "
                f"name={field['name'] or '-'} label={field['label'] or '-'} text={field['text'] or '-'}"
            )
    return results


def switch_frame(driver, frame_name: str | None) -> None:
    driver.switch_to.default_content()
    if not frame_name or frame_name == "main":
        return
    if frame_name.startswith("iframe[") and frame_name.endswith("]"):
        frame_name = frame_name[len("iframe[") : -1]
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for frame in frames:
        if frame.get_attribute("id") == frame_name or frame.get_attribute("name") == frame_name:
            driver.switch_to.frame(frame)
            return
    raise RuntimeError(f"Frame not found: {frame_name}")


def set_value(driver, spec: dict[str, Any], value: str) -> None:
    switch_frame(driver, spec.get("frame"))
    selector = spec["selector"]
    mode = spec.get("mode", "input")
    element = driver.find_element(By.CSS_SELECTOR, selector)
    if mode == "select_text":
        Select(element).select_by_visible_text(value)
    elif mode == "select_value":
        element_value = spec.get("values", {}).get(value, value)
        Select(element).select_by_value(element_value)
    elif mode == "click":
        element.click()
    else:
        element.clear()
        element.send_keys(value)
    time.sleep(float(spec.get("pause", 0.15)))


def click(driver, spec: dict[str, Any]) -> None:
    switch_frame(driver, spec.get("frame"))
    driver.find_element(By.CSS_SELECTOR, spec["selector"]).click()
    time.sleep(float(spec.get("pause", 0.3)))


def apply_records(driver, records: list[dict[str, Any]], config: dict[str, Any]) -> None:
    fields = config.get("fields", {})
    required = ["student", "subject", "standard_code", "level"]
    missing = [name for name in required if name not in fields]
    if missing:
        raise RuntimeError(f"selector config missing fields: {', '.join(missing)}")

    limit = int(config.get("limit", 0) or 0)
    target_records = records[:limit] if limit else records
    level_values = config.get("level_values", {})

    for idx, record in enumerate(target_records, start=1):
        print(
            f"[{idx}/{len(target_records)}] {record['subject']} / {record['student']} / "
            f"{record['standard_code'] or record['assessment']} -> {record['level']}"
        )
        set_value(driver, fields["student"], str(record["student"]))
        set_value(driver, fields["subject"], str(record["subject"]))
        set_value(driver, fields["standard_code"], str(record["standard_code"] or record["assessment"]))
        level = level_values.get(record["level"], record["level"])
        set_value(driver, fields["level"], str(level))
        if "save_button" in fields:
            click(driver, fields["save_button"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", required=True, type=Path, help="Parsed JSON records")
    parser.add_argument("--selector-config", type=Path, help="NEIS selector config JSON")
    parser.add_argument("--diagnose", action="store_true", help="Inspect visible NEIS fields")
    parser.add_argument("--dump", type=Path, help="Diagnostic JSON output")
    parser.add_argument("--dry-run", action="store_true", help="Print summary only")
    parser.add_argument("--apply", action="store_true", help="Actually enter records")
    parser.add_argument("--confirm", help="Must be APPLY_NEIS when using --apply")
    parser.add_argument("--port", type=int, default=REMOTE_PORT)
    args = parser.parse_args()

    records = load_json(args.records)
    record_summary(records)

    if args.dry_run and not args.apply:
        return

    driver = attach(args.port)
    if args.diagnose:
        diagnose(driver, args.dump)
        return

    if not args.apply:
        print("No write action requested. Use --dry-run, --diagnose, or --apply --confirm APPLY_NEIS.")
        return
    if args.confirm != "APPLY_NEIS":
        raise SystemExit("--apply requires --confirm APPLY_NEIS")
    if not args.selector_config:
        raise SystemExit("--apply requires --selector-config")

    config = load_json(args.selector_config)
    apply_records(driver, records, config)


if __name__ == "__main__":
    main()
