const dateInput = document.querySelector("#selectedDate");
const lessonGroups = document.querySelector("#lessonGroups");
const emptyState = document.querySelector("#emptyState");
const viewButtons = [...document.querySelectorAll(".view-button")];
let activeView = "day";

function localIsoDate(date = new Date()) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function weekBounds(value) {
    const day = new Date(`${value}T12:00:00`);
    const monday = new Date(day);
    monday.setDate(day.getDate() - ((day.getDay() + 6) % 7));
    const friday = new Date(monday);
    friday.setDate(monday.getDate() + 4);
    return [localIsoDate(monday), localIsoDate(friday)];
}

function monthBounds(value) {
    const [year, month] = value.split("-").map(Number);
    const start = new Date(year, month - 1, 1, 12);
    const end = new Date(year, month, 0, 12);
    return [localIsoDate(start), localIsoDate(end)];
}

function dateLabel(value, options = { month: "long", day: "numeric", weekday: "short" }) {
    return new Intl.DateTimeFormat("ko-KR", options).format(new Date(`${value}T12:00:00`));
}

function setView(view) {
    activeView = view;
    viewButtons.forEach((button) => button.classList.toggle("is-active", button.dataset.view === view));
    loadLessons();
}

function makeText(tag, className, value) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = value || "";
    return element;
}

function lessonCard(record) {
    const card = document.createElement("article");
    card.className = "lesson-card";

    const period = makeText("div", "period-badge", `${record.period}교시`);
    const body = document.createElement("div");
    body.className = "lesson-body";
    const top = document.createElement("div");
    top.className = "lesson-topline";
    top.append(makeText("span", "subject-name", record.subject));

    const lessonNo = record.lesson_number
        ? `${record.lesson_number}${record.total_lessons ? `/${record.total_lessons}차시` : "차시"}`
        : "";
    if (lessonNo) top.append(makeText("span", "lesson-number", lessonNo));
    body.append(top);

    if (record.unit) body.append(makeText("div", "unit-name", record.unit));
    if (record.content) body.append(makeText("p", "lesson-content", record.content));

    const pages = [record.textbook_page, record.additional_page].filter(Boolean);
    if (pages.length) body.append(makeText("div", "page-note", `교과서 ${pages.join(" · ")}쪽`));
    card.append(period, body);
    return card;
}

async function loadLessons() {
    const selected = dateInput.value || localIsoDate();
    let [start, end] = [selected, selected];
    let title = `${dateLabel(selected)} 수업`;
    if (activeView === "week") {
        [start, end] = weekBounds(selected);
        title = "이번 주 수업";
    } else if (activeView === "month") {
        [start, end] = monthBounds(selected);
        title = `${dateLabel(selected, { year: "numeric", month: "long" })} 수업`;
    }

    document.querySelector("#listTitle").textContent = title;
    document.querySelector("#rangeLabel").textContent = start === end
        ? dateLabel(start)
        : `${dateLabel(start)} ~ ${dateLabel(end)}`;
    document.querySelector("#summaryRange").textContent = start === end ? dateLabel(start) : `${start} ~ ${end}`;
    lessonGroups.replaceChildren();

    try {
        const params = new URLSearchParams({ start_date: start, end_date: end });
        const response = await fetch(`/api/lessons?${params}`);
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "수업 자료를 불러오지 못했습니다.");

        const groups = new Map();
        for (const record of payload.records || []) {
            if (!groups.has(record.date)) groups.set(record.date, []);
            groups.get(record.date).push(record);
        }

        for (const [day, records] of groups) {
            const group = document.createElement("section");
            group.className = "day-group";
            if (start !== end) group.append(makeText("h3", "day-heading", dateLabel(day)));
            const cards = document.createElement("div");
            cards.className = "lesson-list";
            records.forEach((record) => cards.append(lessonCard(record)));
            group.append(cards);
            lessonGroups.append(group);
        }

        document.querySelector("#lessonCount").textContent = String(payload.records?.length || 0);
        emptyState.hidden = Boolean(payload.records?.length);
    } catch (error) {
        emptyState.hidden = false;
        emptyState.querySelector("h3").textContent = "뷰어 서버에 연결하지 못했습니다";
        emptyState.querySelector("p").textContent = error.message;
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
            ? `${status.range_start} ~ ${status.range_end} · ${status.count}개 수업을 가져왔습니다.`
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
document.querySelector("#refreshButton").addEventListener("click", () => {
    loadStatus();
    loadLessons();
});
viewButtons.forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
loadStatus();
loadLessons();
window.setInterval(() => {
    loadStatus();
    loadLessons();
}, 12000);
