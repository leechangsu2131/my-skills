import { getSubjectStyle } from "../lib/constants";
import {
    filterItemsBySubject,
    formatPlacement,
    getActionKey,
    getBridgeRow,
    getLesson,
    getPdfPath,
    getPlannedDate,
    getRecordKey,
    getSubject,
    getTitle,
    getUnit,
    isDoneItem,
} from "../lib/lessonFields";
import {
    formatKoreanDate,
    formatWeekday,
    getMonthGrid,
    getWeekdays,
    shiftDate,
    toIsoDate,
} from "../lib/dateUtils";

const PDF_BASE = "http://127.0.0.1:5000/api/pdf";

function viewById(views, id) {
    return views.find((view) => view.id === id);
}

function StatusBadge({ item }) {
    const done = isDoneItem(item);
    return (
        <span
            className={`rounded-full px-3 py-1 text-xs font-bold ${
                done ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
            }`}
        >
            {done ? "완료됨" : "예정"}
        </span>
    );
}

function ActionButtons({ item, markDone, pullLessonForward, extendSchedule, marking }) {
    const recordKey = getRecordKey(item);
    const bridgeRow = getBridgeRow(item);
    const subject = getSubject(item);
    const rowNumber = item.row_number ?? item._row ?? null;
    const done = isDoneItem(item);
    const doneKey = `done-${bridgeRow || recordKey}`;
    const pullKey = `pull-${bridgeRow}`;
    const extendKey = `extend-${subject}-${rowNumber || "next"}`;

    return (
        <div className="mt-4 flex flex-wrap gap-2">
            {getPdfPath(item) && recordKey && (
                <a
                    href={`${PDF_BASE}/${encodeURIComponent(recordKey)}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-100"
                >
                    PDF 보기
                </a>
            )}
            <button
                className={`inline-flex items-center justify-center rounded-2xl px-4 py-2 text-sm font-bold text-white transition ${
                    done || marking === doneKey
                        ? "cursor-not-allowed bg-slate-300"
                        : "bg-slate-950 hover:-translate-y-0.5"
                }`}
                onClick={() => markDone(item)}
                disabled={done || marking === doneKey}
                type="button"
            >
                {done ? "완료됨" : marking === doneKey ? "처리 중..." : "완료 처리"}
            </button>
            {bridgeRow && !done && (
                <button
                    className={`inline-flex items-center justify-center rounded-2xl border px-4 py-2 text-sm font-bold transition ${
                        marking === pullKey
                            ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
                            : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                    }`}
                    onClick={() => pullLessonForward(item)}
                    disabled={marking === pullKey}
                    type="button"
                >
                    {marking === pullKey ? "조정 중..." : "다음 차시 당겨오기"}
                </button>
            )}
            {!done && (
                <button
                    className={`inline-flex items-center justify-center rounded-2xl border px-4 py-2 text-sm font-bold transition ${
                        marking === extendKey
                            ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
                            : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-white"
                    }`}
                    onClick={() => extendSchedule(subject, rowNumber)}
                    disabled={marking === extendKey}
                    type="button"
                >
                    {marking === extendKey ? "연장 중..." : "이 수업 한 차시 더"}
                </button>
            )}
        </div>
    );
}

function PlacementCard({ item, markDone, pullLessonForward, extendSchedule, marking }) {
    const subject = getSubject(item);
    const style = getSubjectStyle(subject);

    return (
        <article className="rounded-[26px] border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
            <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                    <div className={`flex h-12 w-12 items-center justify-center rounded-2xl text-xl ${style.bg} ${style.accent}`}>
                        {style.icon}
                    </div>
                    <div>
                        <div className={`text-sm font-black ${style.accent}`}>{subject || "과목 미정"}</div>
                        <div className="mt-1 text-xs font-semibold text-slate-400">{formatPlacement(item)}</div>
                    </div>
                </div>
                <div className="flex flex-col items-end gap-2">
                    <StatusBadge item={item} />
                    <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-500">
                        {getLesson(item) || "-"}차시
                    </div>
                </div>
            </div>

            <div className="mt-4 text-base font-bold leading-snug text-slate-900">{getTitle(item)}</div>
            {getUnit(item) && <div className="mt-2 text-sm text-slate-500">{getUnit(item)}</div>}

            <ActionButtons
                item={item}
                markDone={markDone}
                pullLessonForward={pullLessonForward}
                extendSchedule={extendSchedule}
                marking={marking}
            />
        </article>
    );
}

function EmptyState({ text }) {
    return (
        <div className="rounded-3xl border border-dashed border-slate-200 bg-white px-4 py-12 text-center text-sm font-semibold text-slate-400">
            {text}
        </div>
    );
}

function WeeklyColumn({ day, items, markDone, pullLessonForward, extendSchedule, marking }) {
    return (
        <section className="rounded-[26px] border border-slate-200 bg-white/90 p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <div className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">
                        {formatWeekday(day)}
                    </div>
                    <div className="mt-1 text-lg font-black text-slate-900">
                        {formatKoreanDate(day, { month: "numeric", day: "numeric" })}
                    </div>
                </div>
                <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-500">
                    {items.length}개
                </div>
            </div>
            <div className="mt-4 space-y-3">
                {items.length === 0 ? (
                    <div className="rounded-2xl bg-slate-50 px-4 py-8 text-center text-sm font-semibold text-slate-400">
                        수업 없음
                    </div>
                ) : (
                    items.map((item) => (
                        <PlacementCard
                            key={`${getActionKey(item)}-${getPlannedDate(item)}`}
                            item={item}
                            markDone={markDone}
                            pullLessonForward={pullLessonForward}
                            extendSchedule={extendSchedule}
                            marking={marking}
                        />
                    ))
                )}
            </div>
        </section>
    );
}

function CalendarLessonPill({ item }) {
    const subject = getSubject(item);
    const style = getSubjectStyle(subject);
    return (
        <div
            className={`rounded-2xl px-3 py-2 text-xs font-semibold ${style.bg} ${style.accent} ${isDoneItem(item) ? "opacity-70" : ""}`}
            title={`${subject} ${getTitle(item)}`}
        >
            <div className="truncate">{subject}</div>
            <div className="mt-1 truncate text-slate-700">{getTitle(item)}</div>
        </div>
    );
}

function MonthCell({ cell, items, todayIso }) {
    const isToday = cell.iso === todayIso;
    return (
        <div
            className={`min-h-[150px] rounded-[24px] border p-3 ${
                cell.inMonth ? "border-slate-200 bg-white/90" : "border-slate-100 bg-slate-50/70"
            } ${isToday ? "ring-2 ring-sky-400/70" : ""}`}
        >
            <div className="flex items-center justify-between gap-2">
                <div className={`text-sm font-bold ${cell.inMonth ? "text-slate-800" : "text-slate-400"}`}>
                    {cell.date.getDate()}
                </div>
                <div className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-300">
                    {formatWeekday(cell.date)}
                </div>
            </div>
            <div className="mt-3 space-y-2">
                {items.slice(0, 3).map((item) => (
                    <CalendarLessonPill key={`${getActionKey(item)}-${getPlannedDate(item)}`} item={item} />
                ))}
                {items.length > 3 && (
                    <div className="px-1 text-xs font-semibold text-slate-400">+{items.length - 3}개 더 있음</div>
                )}
            </div>
        </div>
    );
}

export function LessonListView({
    views,
    markDone,
    pullLessonForward,
    extendSchedule,
    marking,
    subjectFilter,
    boardDate,
    setBoardDate,
}) {
    const todayView = viewById(views, "today");
    const nextSchoolDayView = viewById(views, "next_school_day");
    const weekView = viewById(views, "thisweek");
    const monthView = viewById(views, "thismonth");

    const todayItems = filterItemsBySubject(todayView?.data, subjectFilter);
    const nextSchoolDayItems = filterItemsBySubject(nextSchoolDayView?.data, subjectFilter);
    const weekItems = filterItemsBySubject(weekView?.data, subjectFilter);
    const monthItems = filterItemsBySubject(monthView?.data, subjectFilter);

    const weekDays = getWeekdays(weekView?.start_date || new Date());
    const weekGroups = Object.fromEntries(weekDays.map((day) => [toIsoDate(day), []]));
    weekItems.forEach((item) => {
        const key = toIsoDate(getPlannedDate(item));
        if (weekGroups[key]) {
            weekGroups[key].push(item);
        }
    });

    const monthGrid = getMonthGrid(monthView?.start_date || new Date());
    const monthGroups = {};
    monthItems.forEach((item) => {
        const key = toIsoDate(getPlannedDate(item));
        monthGroups[key] = monthGroups[key] || [];
        monthGroups[key].push(item);
    });

    const todayIso = toIsoDate(new Date());
    const todayDoneCount = todayItems.filter((item) => isDoneItem(item)).length;

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <section className="rounded-[32px] border border-slate-200 bg-[linear-gradient(135deg,#eff6ff_0%,#f8fbff_45%,#ffffff_100%)] p-6 shadow-sm">
                <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
                    <div>
                        <div className="text-[11px] font-black uppercase tracking-[0.28em] text-sky-600">
                            Placement Board
                        </div>
                        <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-900">
                            오늘, 다음 수업일, 선택한 주, 선택한 달의 배치를 한눈에 봅니다.
                        </h2>
                        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                            완료한 수업도 사라지지 않고 남겨 둡니다. 빠른 조정은 "다음 차시 당겨오기"와
                            "이 수업 한 차시 더" 기준으로 동작합니다.
                        </p>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                        <div className="rounded-[24px] border border-sky-100/70 bg-white/80 px-4 py-4 shadow-sm">
                            <div className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">오늘</div>
                            <div className="mt-2 text-3xl font-black text-slate-900">{todayItems.length}</div>
                            <div className="mt-2 text-sm text-slate-500">{todayDoneCount}개 완료</div>
                        </div>
                        <div className="rounded-[24px] border border-sky-100/70 bg-white/80 px-4 py-4 shadow-sm">
                            <div className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">다음 수업일</div>
                            <div className="mt-2 text-3xl font-black text-slate-900">{nextSchoolDayItems.length}</div>
                            <div className="mt-2 text-sm text-slate-500">{nextSchoolDayView?.date || "미정"}</div>
                        </div>
                        <div className="rounded-[24px] border border-sky-100/70 bg-white/80 px-4 py-4 shadow-sm">
                            <div className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">선택 주</div>
                            <div className="mt-2 text-3xl font-black text-slate-900">{weekItems.length}</div>
                            <div className="mt-2 text-sm text-slate-500">{weekView?.start_date} ~ {weekView?.end_date}</div>
                        </div>
                        <div className="rounded-[24px] border border-sky-100/70 bg-white/80 px-4 py-4 shadow-sm">
                            <div className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">선택 달</div>
                            <div className="mt-2 text-3xl font-black text-slate-900">{monthItems.length}</div>
                            <div className="mt-2 text-sm text-slate-500">달력 보기</div>
                        </div>
                    </div>
                </div>
            </section>

            <div className="grid gap-6 xl:grid-cols-2">
                <section className="rounded-[30px] border border-slate-200 bg-[#fffdfa] p-5 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">TODAY</div>
                            <h3 className="mt-1 text-xl font-black text-slate-900">
                                오늘 수업 {todayView?.date ? `· ${formatKoreanDate(todayView.date)}` : ""}
                            </h3>
                        </div>
                        <div className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm font-bold text-slate-500">
                            {todayItems.length}개
                        </div>
                    </div>
                    <div className="mt-5 space-y-4">
                        {todayItems.length === 0 ? (
                            <EmptyState text="오늘 표시할 수업이 없습니다." />
                        ) : (
                            todayItems.map((item) => (
                                <PlacementCard
                                    key={`${getActionKey(item)}-${getPlannedDate(item)}`}
                                    item={item}
                                    markDone={markDone}
                                    pullLessonForward={pullLessonForward}
                                    extendSchedule={extendSchedule}
                                    marking={marking}
                                />
                            ))
                        )}
                    </div>
                </section>

                <section className="rounded-[30px] border border-slate-200 bg-[#fffdfa] p-5 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">NEXT SCHOOL DAY</div>
                            <h3 className="mt-1 text-xl font-black text-slate-900">
                                다음 수업일 {nextSchoolDayView?.date ? `· ${formatKoreanDate(nextSchoolDayView.date)}` : ""}
                            </h3>
                        </div>
                        <div className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm font-bold text-slate-500">
                            {nextSchoolDayItems.length}개
                        </div>
                    </div>
                    <div className="mt-5 space-y-4">
                        {nextSchoolDayItems.length === 0 ? (
                            <EmptyState text="다음 수업일에 잡힌 수업이 없습니다." />
                        ) : (
                            nextSchoolDayItems.map((item) => (
                                <PlacementCard
                                    key={`${getActionKey(item)}-${getPlannedDate(item)}`}
                                    item={item}
                                    markDone={markDone}
                                    pullLessonForward={pullLessonForward}
                                    extendSchedule={extendSchedule}
                                    marking={marking}
                                />
                            ))
                        )}
                    </div>
                </section>
            </div>

            <section className="space-y-4">
                <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                    <div>
                        <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">WEEK BOARD</div>
                        <h3 className="mt-1 text-2xl font-black text-slate-900">주간 수업 보드</h3>
                        <div className="mt-2 text-sm font-semibold text-slate-500">
                            월요일부터 금요일까지 보여 줍니다.
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        <button
                            className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                            onClick={() => setBoardDate(shiftDate(boardDate, -7))}
                            type="button"
                        >
                            이전주
                        </button>
                        <button
                            className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                            onClick={() => setBoardDate(new Date().toISOString().slice(0, 10))}
                            type="button"
                        >
                            이번주
                        </button>
                        <button
                            className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                            onClick={() => setBoardDate(shiftDate(boardDate, 7))}
                            type="button"
                        >
                            다음주
                        </button>
                        <input
                            type="date"
                            className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 outline-none transition focus:border-slate-950"
                            value={boardDate}
                            onChange={(event) => setBoardDate(event.target.value)}
                        />
                    </div>
                </div>
                <div className="grid gap-4 xl:grid-cols-5">
                    {weekDays.map((day) => (
                        <WeeklyColumn
                            key={toIsoDate(day)}
                            day={day}
                            items={weekGroups[toIsoDate(day)] || []}
                            markDone={markDone}
                            pullLessonForward={pullLessonForward}
                            extendSchedule={extendSchedule}
                            marking={marking}
                        />
                    ))}
                </div>
            </section>

            <section className="space-y-4">
                <div className="flex items-end justify-between gap-4">
                    <div>
                        <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">MONTH BOARD</div>
                        <h3 className="mt-1 text-2xl font-black text-slate-900">월간 달력</h3>
                    </div>
                    <div className="text-sm font-semibold text-slate-500">
                        선택한 주가 속한 달을 달력 형태로 보여 줍니다.
                    </div>
                </div>
                <div className="space-y-3">
                    <div className="grid grid-cols-7 gap-3">
                        {["일", "월", "화", "수", "목", "금", "토"].map((label) => (
                            <div key={label} className="px-2 text-center text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">
                                {label}
                            </div>
                        ))}
                    </div>
                    <div className="space-y-3">
                        {monthGrid.map((week, index) => (
                            <div key={`month-week-${index}`} className="grid grid-cols-7 gap-3">
                                {week.map((cell) => (
                                    <MonthCell
                                        key={cell.iso}
                                        cell={cell}
                                        items={monthGroups[cell.iso] || []}
                                        todayIso={todayIso}
                                    />
                                ))}
                            </div>
                        ))}
                    </div>
                </div>
            </section>
        </div>
    );
}
