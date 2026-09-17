#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Draft Chuseok-week timetable changes in the open NEIS screen.

Default mode is read-only. With `--apply-draft`, this updates the visible
eXBuilder datasets/grid for Mon-Wed periods 5, 6, and 7 in the Chuseok week.
It never clicks Save; saving must be done separately after explicit approval.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


APP_ID = "edu/sw/els/edc/tm/els_edctm00_m00"
TARGET_DATE = "20260925"
TARGET_DAYS = ["mon", "tue", "wed"]
TARGET_PERIODS = ["5", "6", "7"]
DAY_LABELS = {"mon": "월", "tue": "화", "wed": "수"}

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


JS_DRAFT = r"""
return (function(appId, targetDate, periods, days, teacherHint, applyDraft) {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {ok: false, error: "cpr Platform is not available"};

  const app = platform.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id === appId;
  });
  if (!app) return {ok: false, error: "학급시간표관리 app is not open"};

  const dsWeek = app.lookup("dsWeekList");
  const dsTi = app.lookup("dsWeekByClsByTi");
  const dsSubjects = app.lookup("dsAyrSemGrdByEtbSbjt");
  const grid = app.lookup("grdWeekByClsByTi");
  if (!dsWeek || !dsTi || !dsSubjects || !grid) {
    return {ok: false, error: "required timetable controls are missing"};
  }

  function cleanDate(value) {
    return String(value || "").replace(/[^0-9]/g, "");
  }

  function textOf(value) {
    return String(value || "")
      .replace(/<br\s*\/?>/gi, " / ")
      .replace(/<[^>]+>/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function rowObject(ds, r) {
    const row = {};
    const cols = ds.getColumnNames ? ds.getColumnNames() : [];
    cols.forEach(function(col) {
      try { row[col] = ds.getValue(r, col); } catch(e) {}
    });
    return row;
  }

  let week = null;
  for (let r = 0; r < dsWeek.getRowCount(); r++) {
    const begin = cleanDate(dsWeek.getValue(r, "weekBgngYmd"));
    const end = cleanDate(dsWeek.getValue(r, "weekEndYmd"));
    if (begin && end && begin <= targetDate && targetDate <= end) {
      week = rowObject(dsWeek, r);
      week.__rowIndex = r;
      break;
    }
  }
  if (!week) return {ok: false, error: "target week not found"};

  const firstYmd = dsTi.getRowCount() ? cleanDate(dsTi.getValue(0, "monYmd")) : "";
  if (firstYmd !== cleanDate(week.weekBgngYmd)) {
    return {
      ok: false,
      error: "target week is not loaded in dsWeekByClsByTi",
      expectedMonYmd: cleanDate(week.weekBgngYmd),
      actualMonYmd: firstYmd,
      week: week
    };
  }

  const peRows = [];
  for (let r = 0; r < dsSubjects.getRowCount(); r++) {
    const subjectName = String(dsSubjects.getValue(r, "etbSbjtNm") || "");
    if (subjectName.indexOf("체육") < 0) continue;
    peRows.push({
      rowIndex: r,
      etbSbjtCd: dsSubjects.getValue(r, "etbSbjtCd") || "",
      etbSbjtNm: dsSubjects.getValue(r, "etbSbjtNm") || "",
      etbSbjtNmTcrNm: dsSubjects.getValue(r, "etbSbjtNmTcrNm") || "",
      tcrIdfId: dsSubjects.getValue(r, "tcrIdfId") || "",
      userNm: dsSubjects.getValue(r, "userNm") || ""
    });
  }

  const pe = peRows.find(function(row) {
    return teacherHint && String(row.tcrIdfId).indexOf(teacherHint) >= 0;
  }) || peRows.find(function(row) {
    return String(row.tcrIdfId).indexOf("sch9901") >= 0;
  }) || peRows[0];
  if (!pe) return {ok: false, error: "PE subject not found"};

  const targetInfo = "01|" + pe.etbSbjtCd + "|" + pe.tcrIdfId + "|4||";
  const targetOtpt = "<div></div>체육<br/>(" + pe.userNm + "(" + pe.tcrIdfId + "))";
  const changes = [];

  for (let r = 0; r < dsTi.getRowCount(); r++) {
    const pir = String(dsTi.getValue(r, "pir") || dsTi.getValue(r, "pirOtpt") || "").replace(/[^0-9]/g, "");
    if (periods.indexOf(pir) < 0) continue;

    days.forEach(function(day) {
      const infoKey = day + "Info";
      const outKey = day + "Otpt";
      const atrzKey = day + "AtrzInfo";
      const currentInfo = String(dsTi.getValue(r, infoKey) || "");
      const currentOtpt = String(dsTi.getValue(r, outKey) || "");
      const currentLabel = textOf(currentOtpt);
      const ymd = cleanDate(dsTi.getValue(r, day + "Ymd") || "");

      const isEvent = currentInfo.indexOf("|00000|") >= 0 ||
        currentLabel.indexOf("휴업") >= 0 ||
        currentLabel.indexOf("휴일") >= 0 ||
        currentLabel.indexOf("추석") >= 0;
      if (isEvent) return;

      const alreadyTarget = currentInfo === targetInfo;
      const change = {
        rowIndex: r,
        period: pir,
        day: day,
        ymd: ymd,
        currentLabel: currentLabel,
        currentInfo: currentInfo,
        targetLabel: "체육(" + pe.userNm + "(" + pe.tcrIdfId + "))",
        targetInfo: targetInfo,
        alreadyTarget: alreadyTarget
      };
      changes.push(change);

      if (applyDraft && !alreadyTarget) {
        dsTi.setValue(r, infoKey, targetInfo);
        dsTi.setValue(r, outKey, targetOtpt);
        try { dsTi.setValue(r, atrzKey, ""); } catch(e) {}
        try { grid.setCellValue(r, infoKey, targetInfo); } catch(e) {}
        try { grid.setCellValue(r, outKey, targetOtpt); } catch(e) {}
        try { grid.updateRow(r); } catch(e) {}
      }
    });
  }

  if (applyDraft) {
    try { grid.redraw(); } catch(e) {}
  }

  const verification = [];
  for (let r = 0; r < dsTi.getRowCount(); r++) {
    const pir = String(dsTi.getValue(r, "pir") || "").replace(/[^0-9]/g, "");
    if (periods.indexOf(pir) < 0) continue;
    const row = {period: pir};
    days.forEach(function(day) {
      row[day] = {
        ymd: cleanDate(dsTi.getValue(r, day + "Ymd") || ""),
        label: textOf(dsTi.getValue(r, day + "Otpt") || ""),
        info: String(dsTi.getValue(r, day + "Info") || "")
      };
    });
    verification.push(row);
  }

  return {
    ok: true,
    applyDraft: applyDraft,
    week: week,
    selectedPe: pe,
    targetInfo: targetInfo,
    changes: changes,
    verification: verification
  };
})(arguments[0], arguments[1], arguments[2], arguments[3], arguments[4], arguments[5]);
"""


def attach_chrome(port: int):
    os.environ["no_proxy"] = "127.0.0.1,localhost"
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
            pass
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError(f"CDP endpoint is not responding: {exc}") from exc

    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    return webdriver.Chrome(options=opts)


def switch_to_neis_cpr_window(driver) -> bool:
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        try:
            if driver.execute_script("return typeof cpr !== 'undefined';") and "vpn" not in driver.current_url.lower():
                return True
        except Exception:
            pass
    return False


def write_json(prefix: str, data: dict) -> Path:
    path = Path(__file__).parent / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft Chuseok-week PE timetable cells")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--teacher", default="lee2131")
    parser.add_argument("--apply-draft", action="store_true", help="Update the open screen, but do not save")
    args = parser.parse_args()

    try:
        driver = attach_chrome(args.port)
    except Exception as exc:
        print(f"[connect:error] {exc}")
        return 3

    if not switch_to_neis_cpr_window(driver):
        print("[connect:error] cpr Platform이 있는 나이스 화면을 찾지 못했습니다.")
        return 4

    result = driver.execute_script(JS_DRAFT, APP_ID, TARGET_DATE, TARGET_PERIODS, TARGET_DAYS, args.teacher, args.apply_draft)
    path = write_json("chuseok_timetable_draft", result)
    print(f"[draft:json] {path}")

    if not result.get("ok"):
        print("[error]", json.dumps(result, ensure_ascii=False))
        return 1

    week = result.get("week") or {}
    print(f"[week] {week.get('weekCntNm')} | {week.get('event')}")
    pe = result.get("selectedPe") or {}
    print(f"[pe] {pe.get('etbSbjtNmTcrNm')} -> {result.get('targetInfo')}")
    print(f"[mode] {'APPLY_DRAFT_NO_SAVE' if args.apply_draft else 'DRY_RUN'}")
    for change in result.get("changes") or []:
        marker = "same" if change.get("alreadyTarget") else "change"
        day = DAY_LABELS.get(change.get("day"), change.get("day"))
        print(
            f"- [{marker}] {change.get('ymd')} {day} {change.get('period')}교시: "
            f"{change.get('currentLabel') or '(blank)'} -> {change.get('targetLabel')}"
        )

    if args.apply_draft:
        print("[note] 화면 데이터만 반영했습니다. 저장 버튼은 누르지 않았습니다.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
