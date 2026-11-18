/**
 * Demo / seed data for offline-first development.
 * This data mirrors what would come from Supabase tables.
 * Once Supabase is connected, this file serves as fallback only.
 */

export const SUBJECTS = [
    { id: "s1", name: "국어", color: "#005bbf", sort_order: 1 },
    { id: "s2", name: "수학", color: "#e85d04", sort_order: 2 },
    { id: "s3", name: "사회", color: "#6a994e", sort_order: 3 },
    { id: "s4", name: "과학", color: "#9b5de5", sort_order: 4 },
    { id: "s5", name: "도덕", color: "#f4a261", sort_order: 5 },
    { id: "s6", name: "음악", color: "#e76f51", sort_order: 6 },
    { id: "s7", name: "미술", color: "#2a9d8f", sort_order: 7 },
    { id: "s8", name: "체육", color: "#264653", sort_order: 8 },
    { id: "s9", name: "영어", color: "#d62828", sort_order: 9 },
    { id: "s10", name: "실과", color: "#606c38", sort_order: 10 },
];

const today = new Date();
const dayOfWeek = today.getDay();
const monday = new Date(today);
monday.setDate(today.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));

function toLocalDateStr(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function dayStr(offset) {
    const d = new Date(monday);
    d.setDate(monday.getDate() + offset);
    return toLocalDateStr(d);
}

function subjectColor(name) {
    const s = SUBJECTS.find((s) => s.name === name);
    return s ? s.color : "#005bbf";
}

export const DEMO_SLOTS = [
    // Monday
    { id: "sl01", lesson_id: "l01", slot_date: dayStr(0), slot_period: 1, status: "done", subject: "국어", lesson_number: 15, title: "시를 읽고 감상하기", unit: "4. 시의 세계" },
    { id: "sl02", lesson_id: "l02", slot_date: dayStr(0), slot_period: 2, status: "done", subject: "수학", lesson_number: 22, title: "분수의 덧셈", unit: "5. 분수" },
    { id: "sl03", lesson_id: "l03", slot_date: dayStr(0), slot_period: 3, status: "planned", subject: "사회", lesson_number: 8, title: "우리 지역의 문화유산", unit: "2. 우리 고장의 문화" },
    { id: "sl04", lesson_id: "l04", slot_date: dayStr(0), slot_period: 5, status: "planned", subject: "체육", lesson_number: 6, title: "줄넘기 기초", unit: "1. 건강 활동" },
    // Tuesday
    { id: "sl05", lesson_id: "l05", slot_date: dayStr(1), slot_period: 1, status: "planned", subject: "수학", lesson_number: 23, title: "분수의 뺄셈", unit: "5. 분수" },
    { id: "sl06", lesson_id: "l06", slot_date: dayStr(1), slot_period: 2, status: "planned", subject: "국어", lesson_number: 16, title: "시 쓰기 활동", unit: "4. 시의 세계" },
    { id: "sl07", lesson_id: "l07", slot_date: dayStr(1), slot_period: 3, status: "planned", subject: "과학", lesson_number: 10, title: "물의 상태 변화", unit: "3. 물질의 상태" },
    { id: "sl08", lesson_id: "l08", slot_date: dayStr(1), slot_period: 4, status: "planned", subject: "도덕", lesson_number: 4, title: "배려하는 마음", unit: "2. 함께 사는 세상" },
    // Wednesday
    { id: "sl09", lesson_id: "l09", slot_date: dayStr(2), slot_period: 1, status: "planned", subject: "국어", lesson_number: 17, title: "이야기 읽고 인물 파악하기", unit: "5. 이야기 세상" },
    { id: "sl10", lesson_id: "l10", slot_date: dayStr(2), slot_period: 2, status: "planned", subject: "사회", lesson_number: 9, title: "문화유산 보호 방법", unit: "2. 우리 고장의 문화" },
    { id: "sl11", lesson_id: "l11", slot_date: dayStr(2), slot_period: 4, status: "planned", subject: "음악", lesson_number: 5, title: "리코더 연주 — 비행기", unit: "2. 악기와 노래" },
    { id: "sl12", lesson_id: "l12", slot_date: dayStr(2), slot_period: 5, status: "planned", subject: "미술", lesson_number: 3, title: "점과 선으로 표현하기", unit: "1. 표현의 기초" },
    // Thursday
    { id: "sl13", lesson_id: "l13", slot_date: dayStr(3), slot_period: 1, status: "planned", subject: "수학", lesson_number: 24, title: "분수의 합과 차 응용", unit: "5. 분수" },
    { id: "sl14", lesson_id: "l14", slot_date: dayStr(3), slot_period: 2, status: "planned", subject: "과학", lesson_number: 11, title: "물질의 상태 변화 탐구", unit: "3. 물질의 상태" },
    { id: "sl15", lesson_id: "l15", slot_date: dayStr(3), slot_period: 3, status: "planned", subject: "국어", lesson_number: 18, title: "이야기 속 사건 정리하기", unit: "5. 이야기 세상" },
    { id: "sl16", lesson_id: "l16", slot_date: dayStr(3), slot_period: 5, status: "planned", subject: "영어", lesson_number: 7, title: "What Time Is It?", unit: "Unit 4. Time" },
    // Friday
    { id: "sl17", lesson_id: "l17", slot_date: dayStr(4), slot_period: 1, status: "planned", subject: "국어", lesson_number: 19, title: "이야기 감상문 쓰기", unit: "5. 이야기 세상" },
    { id: "sl18", lesson_id: "l18", slot_date: dayStr(4), slot_period: 2, status: "planned", subject: "수학", lesson_number: 25, title: "단원 정리 — 분수", unit: "5. 분수" },
    { id: "sl19", lesson_id: "l19", slot_date: dayStr(4), slot_period: 3, status: "planned", subject: "체육", lesson_number: 7, title: "줄넘기 응용", unit: "1. 건강 활동" },
    { id: "sl20", lesson_id: "l20", slot_date: dayStr(4), slot_period: 4, status: "planned", subject: "실과", lesson_number: 2, title: "안전한 조리 도구 사용", unit: "1. 생활과 기술" },
];

/** Build subject timeline summary from slots */
export function buildSubjectTimeline(slots) {
    const grouped = {};
    for (const slot of slots) {
        if (!grouped[slot.subject]) grouped[slot.subject] = [];
        grouped[slot.subject].push(slot);
    }

    return SUBJECTS.map((s) => {
        const items = grouped[s.name] || [];
        const done = items.filter((i) => i.status === "done").length;
        return {
            subject: s.name,
            color: s.color,
            total: items.length,
            done,
            items,
            progress: items.length > 0 ? Math.round((done / items.length) * 100) : 0,
        };
    }).filter((s) => s.total > 0);
}

/** Group slots by date */
export function groupByDate(slots) {
    const grouped = {};
    for (const slot of slots) {
        if (!grouped[slot.slot_date]) grouped[slot.slot_date] = [];
        grouped[slot.slot_date].push(slot);
    }
    // Sort each day by period
    for (const dateKey of Object.keys(grouped)) {
        grouped[dateKey].sort((a, b) => a.slot_period - b.slot_period);
    }
    return grouped;
}

/** Get today's ISO string */
export function todayStr() {
    return toLocalDateStr(new Date());
}

/** Format date as readable Korean */
export function formatDateKR(dateStr) {
    if (!dateStr) return "";
    const d = new Date(dateStr + "T00:00:00");
    const dayNames = ["일", "월", "화", "수", "목", "금", "토"];
    return `${d.getMonth() + 1}/${d.getDate()} (${dayNames[d.getDay()]})`;
}

/** Format full date */
export function formatDateFull(dateStr) {
    if (!dateStr) return "";
    const d = new Date(dateStr + "T00:00:00");
    return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일`;
}

/** Get the week range for a given date */
export function getWeekRange(dateStr) {
    const d = new Date(dateStr + "T00:00:00");
    const dayOfWeek = d.getDay();
    const mon = new Date(d);
    mon.setDate(d.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
    const fri = new Date(mon);
    fri.setDate(mon.getDate() + 4);
    return {
        start: toLocalDateStr(mon),
        end: toLocalDateStr(fri),
        days: Array.from({ length: 5 }, (_, i) => {
            const day = new Date(mon);
            day.setDate(mon.getDate() + i);
            return toLocalDateStr(day);
        }),
    };
}

export function getMonthMatrix(dateStr) {
    const base = new Date(dateStr + "T00:00:00");
    const year = base.getFullYear();
    const month = base.getMonth();
    const firstOfMonth = new Date(year, month, 1);
    const lastOfMonth = new Date(year, month + 1, 0);
    const startDate = new Date(firstOfMonth);
    startDate.setDate(firstOfMonth.getDate() - firstOfMonth.getDay());
    const endDate = new Date(lastOfMonth);
    endDate.setDate(lastOfMonth.getDate() + (6 - lastOfMonth.getDay()));

    const weeks = [];
    let week = [];
    const cursor = new Date(startDate);

    while (cursor <= endDate) {
        week.push({
            date: new Date(cursor),
            iso: toLocalDateStr(cursor),
            inMonth: cursor.getMonth() === month,
        });

        if (week.length === 7) {
            weeks.push(week);
            week = [];
        }
        cursor.setDate(cursor.getDate() + 1);
    }

    return weeks;
}
