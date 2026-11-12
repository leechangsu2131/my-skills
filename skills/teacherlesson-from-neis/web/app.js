const dateInput = document.querySelector("#selectedDate");
const lessonGroups = document.querySelector("#lessonGroups");
const weekView = document.querySelector("#weekView");
const calendarView = document.querySelector("#calendarView");
const emptyState = document.querySelector("#emptyState");
const viewButtons = [...document.querySelectorAll(".view-button")];
const calendarControls = document.querySelector("#calendarControls");
const weekendInput = document.querySelector("#weekendInput");
const cellHeightInput = document.querySelector("#cellHeightInput");
const cellHeightOutput = document.querySelector("#cellHeightOutput");
let activeView = "day";
let loadSequence = 0;
let visibleRecords = [];
let showWeekends = true;
let cellHeight = 160;
const expandedDates = new Set();

try {
    showWeekends = localStorage.getItem("teacherlessonShowWeekends") !== "false";
    const savedHeight = Number(localStorage.getItem("teacherlessonCalendarCellHeight"));
    if (Number.isFinite(savedHeight) && savedHeight >= 120 && savedHeight <= 360) cellHeight = savedHeight;
} catch (_) { }
weekendInput.checked = showWeekends;
cellHeightInput.value = String(cellHeight);
cellHeightOutput.value = `${cellHeight}px`;

const SUBJECT_COLORS = {
    국어: "#f59e0b", 수학: "#10b981", 사회: "#3b82f6", 과학: "#14b8a6", 도덕: "#84cc16",
    영어: "#818cf8", 음악: "#f97316", 미술: "#ec4899", 체육: "#f43f5e", 창체: "#eab308",
};
const FALLBACK_COLORS = ["#0ea5e9", "#8b5cf6", "#64748b", "#06b6d4", "#a855f7"];

function localIsoDate(date = new Date()) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function parseIsoDate(value) {
    const [year, month, day] = String(value).split("-").map(Number);
    return new Date(year, month - 1, day, 12);
}

function weekDays(value) {
    const monday = parseIsoDate(value);
    monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
    return Array.from({ length: 5 }, (_, index) => {
        const date = new Date(monday);
        date.setDate(monday.getDate() + index);
        return date;
    });
}

function weekBounds(value) {
    const days = weekDays(value);
    return [localIsoDate(days[0]), localIsoDate(days[4])];
}

function monthBounds(value) {
    const [year, month] = value.split("-").map(Number);
    return [localIsoDate(new Date(year, month - 1, 1, 12)), localIsoDate(new Date(year, month, 0, 12))];
}

function monthCells(value) {
    const selected = parseIsoDate(value);
    const first = new Date(selected.getFullYear(), selected.getMonth(), 1, 12);
    const last = new Date(selected.getFullYear(), selected.getMonth() + 1, 0, 12);
    const offset = (first.getDay() + 6) % 7;
    const cellCount = Math.ceil((offset + last.getDate()) / 7) * 7;
    const start = new Date(first);
    start.setDate(first.getDate() - offset);
    return Array.from({ length: cellCount }, (_, index) => {
        const date = new Date(start);
        date.setDate(start.getDate() + index);
        return { date, iso: localIsoDate(date), inMonth: date.getMonth() === selected.getMonth() };
    });
}

function dateLabel(value, options = { month: "long", day: "numeric", weekday: "short" }) {
    return new Intl.DateTimeFormat("ko-KR", options).format(parseIsoDate(value));
}

function shortRange(start, end) {
    const options = { month: "numeric", day: "numeric", weekday: "short" };
    return `${dateLabel(start, options)} ~ ${dateLabel(end, options)}`;
}

function setView(view) {
    activeView = view;
    viewButtons.forEach((button) => {
        const active = button.dataset.view === view;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", String(active));
    });
    updatePeriodControls();
    loadLessons();
}

function updatePeriodControls() {
    const unit = activeView === "month" ? "달" : activeView === "week" ? "주" : "날";
    document.querySelector("#prevPeriod").setAttribute("aria-label", `이전 ${unit}`);
    document.querySelector("#prevPeriod").title = `이전 ${unit}`;
    document.querySelector("#nextPeriod").setAttribute("aria-label", `다음 ${unit}`);
    document.querySelector("#nextPeriod").title = `다음 ${unit}`;
}

function shiftPeriod(direction) {
    const date = parseIsoDate(dateInput.value || localIsoDate());
    if (activeView === "month") {
        const originalDay = date.getDate();
        date.setDate(1);
        date.setMonth(date.getMonth() + direction);
        const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
        date.setDate(Math.min(originalDay, lastDay));
    } else {
        date.setDate(date.getDate() + direction * (activeView === "week" ? 7 : 1));
    }
    dateInput.value = localIsoDate(date);
    loadLessons();
}

function makeText(tag, className, value) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = value || "";
    return element;
}

function colorForSubject(subject) {
    if (SUBJECT_COLORS[subject]) return SUBJECT_COLORS[subject];
    let hash = 0;
    for (const char of String(subject || "")) hash = (hash * 31 + char.charCodeAt(0)) | 0;
    return FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length];
}

function lessonCard(record, compact = false) {
    const card = document.createElement("article");
    card.className = `lesson-card${compact ? " is-compact" : ""}`;
    card.style.setProperty("--subject-color", colorForSubject(record.subject));

    card.append(makeText("div", "period-badge", `${record.period}교시`));
    const body = document.createElement("div");
    body.className = "lesson-body";
    const top = document.createElement("div");
    top.className = "lesson-topline";
    top.append(makeText("span", "subject-name", record.subject || "과목 미정"));

    const lessonNo = record.lesson_number
        ? `${record.lesson_number}${record.total_lessons ? `/${record.total_lessons}차시` : "차시"}`
        : "";
    if (lessonNo && !compact) top.append(makeText("span", "lesson-number", lessonNo));
    body.append(top);

    if (!compact && record.unit) body.append(makeText("div", "unit-name", record.unit));
    if (record.content) body.append(makeText("p", "lesson-content", record.content));
    if (!compact) {
        const pages = [record.textbook_page, record.additional_page].filter(Boolean);
        if (pages.length) body.append(makeText("div", "page-note", `교과서 ${pages.join(" · ")}쪽`));
    }
    card.append(body);
    return card;
}

function groupedByDate(records) {
    const groups = new Map();
    for (const record of records) {
        if (!groups.has(record.date)) groups.set(record.date, []);
        groups.get(record.date).push(record);
    }
    return groups;
}

function renderDay(records, selected) {
    lessonGroups.replaceChildren();
    emptyState.hidden = Boolean(records.length);
    if (!records.length) {
        emptyState.querySelector("h3").textContent = "이 날짜에는 수업 자료가 없습니다";
        emptyState.querySelector("p").textContent = "다른 날짜를 선택하거나 NEIS 주간학습 자료가 동기화됐는지 확인해 주세요.";
        return;
    }
    for (const record of records) lessonGroups.append(lessonCard(record));
}

function renderWeek(records, selected) {
    weekView.replaceChildren();
    emptyState.hidden = true;
    const groups = groupedByDate(records);
    const today = localIsoDate();

    for (const date of weekDays(selected)) {
        const iso = localIsoDate(date);
        const lessons = groups.get(iso) || [];
        const column = document.createElement("section");
        column.className = `week-day${iso === today ? " is-today" : ""}${iso === selected ? " is-selected" : ""}`;

        const heading = document.createElement("header");
        heading.className = "week-day-heading";
        const dayCopy = document.createElement("div");
        dayCopy.append(
            makeText("div", "weekday-name", dateLabel(iso, { weekday: "long" })),
            makeText("h3", "weekday-date", dateLabel(iso, { month: "long", day: "numeric" })),
        );
        if (iso === today) dayCopy.append(makeText("span", "today-marker", "오늘"));
        heading.append(dayCopy, makeText("span", "lesson-count", `${lessons.length}교시`));
        column.append(heading);

        const list = document.createElement("div");
        list.className = "week-lesson-list";
        if (lessons.length) lessons.forEach((lesson) => list.append(lessonCard(lesson)));
        else list.append(makeText("div", "week-empty", "수업 없음"));
        column.append(list);
        weekView.append(column);
    }
    weekView.append(makeText("div", "view-caption", "월요일부터 금요일까지 · 수업 자료가 없는 날도 함께 표시합니다."));
}

function renderMonth(records, selected) {
    calendarView.replaceChildren();
    emptyState.hidden = true;
    const groups = groupedByDate(records);
    const today = localIsoDate();
    const columns = showWeekends ? 7 : 5;
    const headings = document.createElement("div");
    headings.className = "calendar-weekdays";
    headings.style.setProperty("--calendar-columns", String(columns));
    const weekdayNames = showWeekends ? ["월", "화", "수", "목", "금", "토", "일"] : ["월", "화", "수", "목", "금"];
    weekdayNames.forEach((name, index) => {
        const label = makeText("div", `calendar-weekday${index > 4 ? " is-weekend" : ""}`, name);
        headings.append(label);
    });
    calendarView.append(headings);

    const grid = document.createElement("div");
    grid.className = "calendar-grid";
    grid.style.setProperty("--calendar-columns", String(columns));
    grid.style.setProperty("--calendar-cell-height", `${cellHeight}px`);
    const visibleLessonLimit = Math.max(3, Math.floor((cellHeight - 52) / 36));
    const cells = monthCells(selected).filter((cell) => showWeekends || (cell.date.getDay() !== 0 && cell.date.getDay() !== 6));
    for (const cell of cells) {
        const lessons = groups.get(cell.iso) || [];
        const day = document.createElement("article");
        day.className = `calendar-day${cell.inMonth ? "" : " is-outside"}${cell.iso === today ? " is-today" : ""}${cell.iso === selected ? " is-selected" : ""}`;
        day.dataset.date = cell.iso;
        if (cell.inMonth) {
            day.setAttribute("aria-label", `${dateLabel(cell.iso, { year: "numeric", month: "long", day: "numeric" })}, 수업 ${lessons.length}개`);
        }

        const top = document.createElement("div");
        top.className = "calendar-day-top";
        if (cell.inMonth) {
            const dateButton = makeText("button", "calendar-date-button", String(cell.date.getDate()));
            dateButton.type = "button";
            dateButton.title = "눌러서 하루 수업 보기";
            dateButton.addEventListener("click", () => {
                dateInput.value = cell.iso;
                setView("day");
            });
            top.append(dateButton);
        } else {
            top.append(makeText("span", "calendar-date", String(cell.date.getDate())));
        }
        if (lessons.length) top.append(makeText("span", "calendar-count", `${lessons.length}교시`));
        else if (cell.iso === today) top.append(makeText("span", "today-marker", "오늘"));
        day.append(top);

        const previews = document.createElement("div");
        previews.className = "month-lesson-list";
        const expanded = expandedDates.has(cell.iso);
        const visibleLessons = expanded ? lessons : lessons.slice(0, visibleLessonLimit);
        for (const lesson of visibleLessons) {
            const preview = document.createElement("div");
            preview.className = "month-lesson";
            preview.style.setProperty("--subject-color", colorForSubject(lesson.subject));
            preview.append(
                makeText("span", "month-period", `${lesson.period}교시`),
                makeText("span", "month-subject", lesson.subject || "과목 미정"),
            );
            const summary = lesson.content || lesson.unit;
            if (summary) preview.append(makeText("span", "month-content", summary));
            previews.append(preview);
        }
        if (lessons.length > visibleLessonLimit) {
            const moreButton = makeText("button", "month-more", expanded ? "접기" : `+ ${lessons.length - visibleLessonLimit}개 수업`);
            moreButton.type = "button";
            moreButton.dataset.expandDate = cell.iso;
            moreButton.setAttribute("aria-expanded", String(expanded));
            moreButton.addEventListener("click", () => {
                if (expandedDates.has(cell.iso)) expandedDates.delete(cell.iso);
                else expandedDates.add(cell.iso);
                renderMonth(records, selected);
                requestAnimationFrame(() => calendarView.querySelector(`[data-expand-date="${cell.iso}"]`)?.focus());
            });
            previews.append(moreButton);
        }
        day.append(previews);
        grid.append(day);
    }
    calendarView.append(grid);
    if (!records.length) {
        calendarView.append(makeText("div", "calendar-note", "이 달에 저장된 수업 자료가 없습니다."));
    }
}

function setEmptyError(message) {
    emptyState.hidden = false;
    emptyState.querySelector("h3").textContent = "뷰어 서버에 연결하지 못했습니다";
    emptyState.querySelector("p").textContent = message;
}

async function loadLessons() {
    const sequence = ++loadSequence;
    const selected = dateInput.value || localIsoDate();
    let [start, end] = [selected, selected];
    let title = `${dateLabel(selected)} 수업`;
    if (activeView === "week") {
        [start, end] = weekBounds(selected);
        title = "주간 수업 보드";
    } else if (activeView === "month") {
        [start, end] = monthBounds(selected);
        title = `${dateLabel(selected, { year: "numeric", month: "long" })} 수업 달력`;
    }

    document.querySelector("#listTitle").textContent = title;
    document.querySelector("#rangeLabel").textContent = start === end ? dateLabel(start) : shortRange(start, end);
    document.querySelector("#summaryRange").textContent = activeView === "day"
        ? dateLabel(start)
        : activeView === "week"
            ? shortRange(start, end)
            : dateLabel(selected, { year: "numeric", month: "long" });
    lessonGroups.hidden = activeView !== "day";
    weekView.hidden = activeView !== "week";
    calendarView.hidden = activeView !== "month";
    calendarControls.hidden = activeView !== "month";
    emptyState.hidden = true;

    try {
        const params = new URLSearchParams({ start_date: start, end_date: end });
        const response = await fetch(`/api/lessons?${params}`);
        const payload = await response.json();
        if (sequence !== loadSequence) return;
        if (!response.ok) throw new Error(payload.error || "수업 자료를 불러오지 못했습니다.");

        const records = (payload.records || []).sort((a, b) =>
            a.date.localeCompare(b.date) || Number(a.period) - Number(b.period) || a.subject.localeCompare(b.subject),
        );
        visibleRecords = records;
        document.querySelector("#lessonCount").textContent = String(records.length);
        if (activeView === "week") renderWeek(records, selected);
        else if (activeView === "month") renderMonth(records, selected);
        else renderDay(records, selected);
    } catch (error) {
        if (sequence === loadSequence) setEmptyError(error.message);
    }
}

async function loadStatus() {
    try {
        const response = await fetch("/api/status");
        const status = await response.json();
        document.querySelector("#lastImported").textContent = status.last_imported_at
            ? new Intl.DateTimeFormat("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(status.last_imported_at))
            : "-";
        document.querySelector("#syncStatus").textContent = status.count
            ? `${status.count}개 저장 · 최근 가져온 ${status.range_start} ~ ${status.range_end}`
            : "NEIS 자료를 아직 가져오지 않았습니다.";
    } catch {
        document.querySelector("#syncStatus").textContent = "뷰어 서버에 연결할 수 없습니다.";
    }
}

dateInput.value = localIsoDate();
dateInput.addEventListener("change", loadLessons);
document.querySelector("#todayButton").addEventListener("click", () => {
    dateInput.value = localIsoDate();
    loadLessons();
});
document.querySelector("#prevPeriod").addEventListener("click", () => shiftPeriod(-1));
document.querySelector("#nextPeriod").addEventListener("click", () => shiftPeriod(1));
document.querySelector("#refreshButton").addEventListener("click", () => {
    loadStatus();
    loadLessons();
});
viewButtons.forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
weekendInput.addEventListener("change", () => {
    showWeekends = weekendInput.checked;
    try { localStorage.setItem("teacherlessonShowWeekends", String(showWeekends)); } catch (_) { }
    if (activeView === "month") renderMonth(visibleRecords, dateInput.value || localIsoDate());
});
cellHeightInput.addEventListener("input", () => {
    cellHeight = Number(cellHeightInput.value);
    cellHeightOutput.value = `${cellHeight}px`;
    if (activeView === "month") renderMonth(visibleRecords, dateInput.value || localIsoDate());
});
cellHeightInput.addEventListener("change", () => {
    try { localStorage.setItem("teacherlessonCalendarCellHeight", String(cellHeight)); } catch (_) { }
});
updatePeriodControls();
loadStatus();
loadLessons();
window.setInterval(() => {
    loadStatus();
    loadLessons();
}, 12000);
