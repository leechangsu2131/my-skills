#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a read-only plan for the Chuseok-week timetable adjustment.

This script attaches to the logged-in NEIS Chrome session, inspects the open
`학급시간표관리` eXBuilder app, and prints the cells that would need to be set
to PE for periods 5, 6, and 7. It does not modify data and never saves.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


APP_ID = "edu/sw/els/edc/tm/els_edctm00_m00"
DEFAULT_CHUSEOK_DATE = "20260925"
DEFAULT_PERIODS = "5,6,7"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


JS_INSPECT_TIMETABLE = r"""
return (function(appId, targetDate, periodsCsv, teacherHint) {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {ok: false, error: "cpr Platform is not available"};

  const app = platform.getAllRunningAppInstances().find(function(ai) {
    return ai && ai.app && ai.app.id === appId;
  });
  if (!app) {
    return {
      ok: false,
      error: "학급시간표관리 app is not open",
      runningApps: platform.getAllRunningAppInstances().map(function(ai) {
        return ai && ai.app && ai.app.id;
      }).filter(Boolean)
    };
  }

  function columnsOf(ds) {
    try { if (ds.getColumnNames) return ds.getColumnNames(); } catch(e) {}
    const cols = [];
    try {
      if (ds.getColumnCount && ds.getColumn) {
        for (let i = 0; i < ds.getColumnCount(); i++) {
          const col = ds.getColumn(i);
          cols.push(col && (col.columnName || col.name || String(col)));
        }
      }
    } catch(e) {}
    return cols.filter(Boolean);
  }

  function rowObject(ds, r) {
    const row = {};
    columnsOf(ds).forEach(function(col) {
      try { row[col] = ds.getValue(r, col); } catch(e) {}
    });
    return row;
  }

  function dsRows(id) {
    const ds = app.lookup(id);
    if (!ds || !ds.getRowCount) return [];
    const rows = [];
    for (let r = 0; r < ds.getRowCount(); r++) {
      const row = rowObject(ds, r);
      row.__rowIndex = r;
      rows.push(row);
    }
    return rows;
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

  function mmddOf(yyyymmdd) {
    const date = cleanDate(yyyymmdd);
    if (date.length < 8) return "";
    return String(Number(date.slice(4, 6))) + "/" + String(Number(date.slice(6, 8)));
  }

  const periods = String(periodsCsv || "").split(",").map(function(v) {
    return String(v).trim();
  }).filter(Boolean);

  const weeks = dsRows("dsWeekList");
  const schedule = dsRows("dsWeekByClsByTi");
  const subjects = dsRows("dsAyrSemGrdByEtbSbjt").concat(dsRows("dsEtbSbjt"));

  const controls = {};
  ["dtiSryYmd", "dtiEndYmd", "cmbSem", "cmbUdcAuth", "cmbGrade", "cmbCls", "grdWeek", "grdWeekByClsByTi"].forEach(function(id) {
    const c = app.lookup(id);
    if (c) controls[id] = {
      id: id,
      type: c.type || "",
      value: typeof c.value === "undefined" || c.value === null ? "" : String(c.value),
      fieldLabel: c.fieldLabel || ""
    };
  });

  const weekMatches = weeks.filter(function(row) {
    const begin = cleanDate(row.weekBgngYmd || row.bgngYmd || row.bgnYmd || "");
    const end = cleanDate(row.weekEndYmd || row.endYmd || "");
    if (begin && end && begin <= targetDate && targetDate <= end) return true;

    const joined = Object.keys(row).map(function(k) { return cleanDate(row[k]); }).join(" ");
    if (joined.indexOf(targetDate) >= 0) return true;

    const mmdd = targetDate.slice(4, 6).replace(/^0/, "") + "/" + targetDate.slice(6, 8).replace(/^0/, "");
    return String(row.event || row.eventNm || "").indexOf(mmdd) >= 0;
  });
  const targetWeek = weekMatches[0] || null;
  const eventText = targetWeek ? String(targetWeek.event || "") : "";

  const peSubjects = subjects.filter(function(row) {
    const name = String(row.etbSbjtNm || row.sbjtNm || row.subjectName || "");
    const joined = JSON.stringify(row);
    return name.indexOf("체육") >= 0 || joined.indexOf("체육") >= 0;
  }).map(function(row) {
    return {
      etbSbjtCd: row.etbSbjtCd || row.ettSbjtCd || row.sbjtCd || "",
      etbSbjtNm: row.etbSbjtNm || row.sbjtNm || "",
      etbSbjtNmTcrNm: row.etbSbjtNmTcrNm || "",
      tcrNm: row.tcrNm || "",
      tcrIdfId: row.tcrIdfId || row.tcrId || "",
      rowIndex: row.__rowIndex
    };
  });

  let selectedPe = peSubjects.find(function(s) {
    return teacherHint && String(s.tcrIdfId).indexOf(teacherHint) >= 0;
  });
  if (!selectedPe) {
    selectedPe = peSubjects.find(function(s) {
      return String(s.tcrIdfId).indexOf("sch9901") >= 0;
    }) || peSubjects[0] || null;
  }

  const days = [
    ["mon", "월"],
    ["tue", "화"],
    ["wed", "수"],
    ["thu", "목"],
    ["fri", "금"],
    ["sat", "토"],
    ["sun", "일"]
  ];

  const currentRows = schedule.map(function(row) {
    const out = {
      rowIndex: row.__rowIndex,
      pir: row.pir || row.pirOtpt || row.PIR || "",
      pirOtpt: row.pirOtpt || ""
    };
    days.forEach(function(day) {
      out[day[0]] = textOf(row[day[0] + "Otpt"]);
      out[day[0] + "Info"] = row[day[0] + "Info"] || "";
    });
    return out;
  });

  const proposed = [];
  schedule.forEach(function(row) {
    const pir = String(row.pir || row.pirOtpt || row.PIR || "").replace(/[^0-9]/g, "");
    if (periods.indexOf(pir) < 0) return;

    days.forEach(function(day) {
      const infoKey = day[0] + "Info";
      const outKey = day[0] + "Otpt";
      const info = String(row[infoKey] || "");
      const label = textOf(row[outKey]);
      const ymd = row[day[0] + "Ymd"] || "";
      const dayEvent = eventText.indexOf(mmddOf(ymd)) >= 0;

      if (day[0] === "sat" || day[0] === "sun") return;
      if (dayEvent || info.indexOf("|00000|") >= 0 || info.indexOf("9011") >= 0) return;
      if (label.indexOf("휴업") >= 0 || label.indexOf("휴일") >= 0 || label.indexOf("추석") >= 0) return;

      const currentSubject = label ? label.split("/")[0].trim() : "";
      const targetInfo = selectedPe
        ? "01|" + selectedPe.etbSbjtCd + "|" + selectedPe.tcrIdfId + "|4||"
        : "";
      const targetLabel = selectedPe
        ? "체육(" + (selectedPe.tcrNm || selectedPe.etbSbjtNmTcrNm || selectedPe.tcrIdfId) + ")"
        : "체육";

      proposed.push({
        period: pir,
        dayKey: day[0],
        day: day[1],
        rowIndex: row.__rowIndex,
        current: currentSubject,
        currentInfo: info,
        target: targetLabel,
        targetInfo: targetInfo,
        alreadyTarget: info === targetInfo || currentSubject.indexOf("체육") >= 0
      });
    });
  });

  return {
    ok: true,
    appId: app.app && app.app.id,
    controls: controls,
    weekRows: weeks,
    targetDate: targetDate,
    weekMatches: weekMatches,
    weekCount: weeks.length,
    scheduleRows: currentRows,
    scheduleRowCount: schedule.length,
    peSubjects: peSubjects,
    selectedPe: selectedPe,
    proposedChanges: proposed
  };
})(arguments[0], arguments[1], arguments[2], arguments[3]);
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
    parser = argparse.ArgumentParser(description="Read-only Chuseok-week timetable change planner")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--target-date", default=DEFAULT_CHUSEOK_DATE, help="YYYYMMDD inside the target week")
    parser.add_argument("--periods", default=DEFAULT_PERIODS, help="Comma-separated periods to set to PE")
    parser.add_argument("--teacher", default="lee2131", help="Prefer this PE teacher id")
    args = parser.parse_args()

    try:
        driver = attach_chrome(args.port)
    except Exception as exc:
        print(f"[connect:error] {exc}")
        return 3

    if not switch_to_neis_cpr_window(driver):
        print("[connect:error] cpr Platform이 있는 나이스 화면을 찾지 못했습니다.")
        return 4

    print(f"[connect] {driver.title}")
    print(f"[url] {driver.current_url}")
    result = driver.execute_script(JS_INSPECT_TIMETABLE, APP_ID, args.target_date, args.periods, args.teacher)
    path = write_json("chuseok_timetable_plan", result)
    print(f"[plan:json] {path}")

    if not result.get("ok"):
        print(f"[error] {result.get('error')}")
        running = result.get("runningApps") or []
        if running:
            print("[running apps]")
            for app_id in running:
                print(f"- {app_id}")
        return 1

    print(f"[app] {result.get('appId')}")
    print(f"[week] dsWeekList rows={result.get('weekCount')} matches={len(result.get('weekMatches') or [])}")
    for row in result.get("weekMatches") or []:
        print("[week:match]", json.dumps(row, ensure_ascii=False))

    print(f"[schedule] rows={result.get('scheduleRowCount')}")
    print("[pe:selected]", json.dumps(result.get("selectedPe"), ensure_ascii=False))
    print("[pe:candidates]")
    for subject in result.get("peSubjects") or []:
        print("-", json.dumps(subject, ensure_ascii=False))

    changes = result.get("proposedChanges") or []
    print(f"[proposed] {len(changes)} candidate cells for periods {args.periods}")
    for item in changes:
        marker = "same" if item.get("alreadyTarget") else "change"
        print(
            f"- [{marker}] {item.get('day')} {item.get('period')}교시: "
            f"{item.get('current') or '(blank)'} -> {item.get('target')} | {item.get('targetInfo')}"
        )

    if not changes:
        print("[note] 현재 선택 주간 시간표가 비어 있거나, 대상 교시 데이터가 아직 로드되지 않았습니다.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
