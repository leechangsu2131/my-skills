import { getSubjectStyle, subjectMatches } from "../lib/constants";
import {
    formatPlacement,
    getActionKey,
    getBridgeRow,
    getLesson,
    getPdfPath,
    getRecordKey,
    getSubject,
    getTitle,
    getUnit,
    isDoneItem,
} from "../lib/lessonFields";
import { formatKoreanDate } from "../lib/dateUtils";

const PDF_BASE = "http://127.0.0.1:5000/api/pdf";

function viewById(views, id) {
    return views.find((view) => view.id === id);
}

function ActivityPanel({ historyView, subjectFilter }) {
    const logs = (historyView?.data || []).filter((log) => subjectMatches(log.subject, subjectFilter));

    if (logs.length === 0) {
        return (
            <section className="rounded-[28px] border border-slate-200 bg-white/85 p-5 shadow-sm">
                <div className="text-sm font-bold text-slate-900">최근 활동</div>
                <p className="mt-3 text-sm text-slate-500">
                    {subjectFilter
                        ? `${subjectFilter} 관련 최근 활동이 아직 없습니다.`
                        : "표시할 최근 활동이 아직 없습니다."}
                </p>
            </section>
        );
    }

    return (
        <section className="rounded-[28px] border border-slate-200 bg-white/85 p-5 shadow-sm">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-black tracking-[0.2em] text-slate-400">RECENT ACTIVITY</h3>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-500">
                    {logs.length}건
                </span>
            </div>
            <div className="mt-5 space-y-4">
                {logs.slice(0, 8).map((log, index) => (
                    <div key={`${log.timestamp}-${index}`} className="flex gap-3">
                        <div className="mt-1 h-2.5 w-2.5 rounded-full bg-sky-500" />
                        <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-3">
                                <div className="truncate text-sm font-bold text-slate-900">
                                    {log.subject || "과목 미정"}
                                </div>
                                <div className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">
                                    {log.action}
                                </div>
                            </div>
                            <div className="mt-1 text-sm text-slate-500">{log.details}</div>
                            <div className="mt-1 text-xs text-slate-400">
                                {new Date(log.timestamp).toLocaleString("ko-KR")}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
}

function TimelineRow({ item }) {
    const subject = getSubject(item);
    const style = getSubjectStyle(subject);
    const done = isDoneItem(item);

    return (
        <div className="rounded-2xl border border-slate-100 bg-slate-50/80 px-4 py-3">
            <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                    <div className="truncate text-sm font-bold text-slate-900">{getTitle(item)}</div>
                    <div className="mt-1 text-xs text-slate-500">
                        {formatPlacement(item)}
                        {getUnit(item) ? ` · ${getUnit(item)}` : ""}
                    </div>
                </div>
                <div className={`rounded-full px-3 py-1 text-[11px] font-bold ${style.bg} ${done ? "text-slate-500" : style.accent}`}>
                    {done ? "완료" : `${getLesson(item) || "-"}차시`}
                </div>
            </div>
        </div>
    );
}

function SubjectCard({ subject, payload, markDone, pullLessonForward, extendSchedule, marking }) {
    const style = getSubjectStyle(subject);
    const nextItem = payload?.next || null;
    const upcoming = payload?.upcoming || [];
    const recent = payload?.recent || [];
    const completedCount = payload?.completed_count || 0;
    const totalCount = payload?.total_count || 0;
    const bridgeRow = getBridgeRow(nextItem);
    const recordKey = getRecordKey(nextItem);
    const rowNumber = nextItem?.row_number ?? nextItem?._row ?? null;
    const doneKey = `done-${bridgeRow || recordKey}`;
    const pullKey = `pull-${bridgeRow}`;
    const extendKey = `extend-${subject}-${rowNumber || "next"}`;

    return (
        <article className="rounded-[30px] border border-slate-200 bg-white/90 p-5 shadow-sm shadow-slate-200/40">
            <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                    <div className={`flex h-14 w-14 items-center justify-center rounded-2xl text-2xl ${style.bg} ${style.accent}`}>
                        {style.icon}
                    </div>
                    <div>
                        <h3 className={`text-lg font-black ${style.accent}`}>{subject}</h3>
                        <p className="text-sm text-slate-500">
                            {completedCount}/{totalCount}개 완료
                        </p>
                    </div>
                </div>
                <div className={`rounded-full px-3 py-1 text-xs font-bold ${style.bg} ${style.accent}`}>
                    {upcoming.length}개 남음
                </div>
            </div>

            <div className="mt-5 rounded-[24px] border border-slate-100 bg-slate-50/80 p-4">
                <div className="flex items-center justify-between gap-3">
                    <div className="text-xs font-black uppercase tracking-[0.22em] text-slate-400">다음 수업</div>
                    {nextItem && (
                        <div className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-500 shadow-sm">
                            {formatPlacement(nextItem)}
                        </div>
                    )}
                </div>

                {nextItem ? (
                    <>
                        <div className="mt-3 text-lg font-bold leading-snug text-slate-900">{getTitle(nextItem)}</div>
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-500">
                            <span className="rounded-full bg-white px-3 py-1 shadow-sm">{getLesson(nextItem) || "-"}차시</span>
                            {getUnit(nextItem) && <span className="rounded-full bg-white px-3 py-1 shadow-sm">{getUnit(nextItem)}</span>}
                            <span className="rounded-full bg-white px-3 py-1 shadow-sm">
                                {nextItem.planned_date ? formatKoreanDate(nextItem.planned_date) : "날짜 미정"}
                            </span>
                        </div>
                        <div className="mt-4 flex flex-wrap gap-2">
                            {getPdfPath(nextItem) && recordKey && (
                                <a
                                    href={`${PDF_BASE}/${encodeURIComponent(recordKey)}`}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-flex items-center justify-center rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                                >
                                    PDF 보기
                                </a>
                            )}
                            <button
                                className={`inline-flex items-center justify-center rounded-2xl px-4 py-2 text-sm font-bold text-white transition ${
                                    marking === doneKey
                                        ? "cursor-not-allowed bg-slate-300"
                                        : "bg-slate-950 hover:-translate-y-0.5"
                                }`}
                                onClick={() => markDone(nextItem)}
                                disabled={marking === doneKey}
                                type="button"
                            >
                                {marking === doneKey ? "처리 중..." : "완료 처리"}
                            </button>
                            {bridgeRow && (
                                <button
                                    className={`inline-flex items-center justify-center rounded-2xl border px-4 py-2 text-sm font-bold transition ${
                                        marking === pullKey
                                            ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
                                            : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-white"
                                    }`}
                                    onClick={() => pullLessonForward(nextItem)}
                                    disabled={marking === pullKey}
                                    type="button"
                                >
                                    {marking === pullKey ? "조정 중..." : "다음 차시 당겨오기"}
                                </button>
                            )}
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
                        </div>
                    </>
                ) : (
                    <div className="mt-3 rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-6 text-center text-sm font-semibold text-slate-400">
                        현재 배치된 다음 수업이 없습니다.
                    </div>
                )}
            </div>

            <div className="mt-5 grid gap-4 xl:grid-cols-2">
                <section>
                    <div className="mb-3 text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">UPCOMING</div>
                    <div className="space-y-3">
                        {upcoming.length === 0 ? (
                            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm font-semibold text-slate-400">
                                남은 수업이 없습니다.
                            </div>
                        ) : (
                            upcoming.slice(0, 5).map((item) => (
                                <TimelineRow key={`${getActionKey(item)}-${item.planned_date}`} item={item} />
                            ))
                        )}
                    </div>
                </section>
                <section>
                    <div className="mb-3 text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">RECENTLY DONE</div>
                    <div className="space-y-3">
                        {recent.length === 0 ? (
                            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm font-semibold text-slate-400">
                                아직 완료한 수업 기록이 없습니다.
                            </div>
                        ) : (
                            recent.map((item) => (
                                <TimelineRow key={`${getActionKey(item)}-${item.planned_date}`} item={item} />
                            ))
                        )}
                    </div>
                </section>
            </div>
        </article>
    );
}

export function DashboardView({
    views,
    markDone,
    pullLessonForward,
    extendSchedule,
    marking,
    subjectFilter,
}) {
    const historyView = viewById(views, "history");
    const timelineView = viewById(views, "subject_timeline");
    const timelineData = timelineView?.data || {};
    const subjects = Object.keys(timelineData).filter((subject) => subjectMatches(subject, subjectFilter));

    const totals = subjects.reduce(
        (accumulator, subject) => {
            const payload = timelineData[subject] || {};
            accumulator.total += payload.total_count || 0;
            accumulator.completed += payload.completed_count || 0;
            accumulator.upcoming += (payload.upcoming || []).length;
            return accumulator;
        },
        { total: 0, completed: 0, upcoming: 0 },
    );

    if (subjects.length === 0) {
        return (
            <div className="rounded-[28px] border border-slate-200 bg-white p-8 text-center text-slate-500 shadow-sm">
                진도 현황 데이터를 찾지 못했습니다.
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <section className="rounded-[32px] border border-slate-200 bg-[linear-gradient(135deg,#0f172a_0%,#1e293b_55%,#334155_100%)] p-6 text-white shadow-xl shadow-slate-900/10">
                <div className="grid gap-6 lg:grid-cols-[1.3fr_0.9fr] lg:items-end">
                    <div>
                        <div className="text-[11px] font-black uppercase tracking-[0.28em] text-slate-300">Timeline Board</div>
                        <h2 className="mt-3 text-3xl font-black tracking-tight">
                            퍼센트보다 실제 수업 흐름이 먼저 보이도록 정리했습니다.
                        </h2>
                        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-200">
                            과목별로 다음 수업이 언제인지, 앞으로 어떤 수업이 잡혀 있는지, 최근에 무엇을 마쳤는지
                            바로 볼 수 있습니다.
                        </p>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-3">
                        <div className="rounded-[24px] border border-white/10 bg-white/10 p-4 backdrop-blur">
                            <div className="text-xs font-black uppercase tracking-[0.22em] text-slate-300">남은 수업</div>
                            <div className="mt-2 text-4xl font-black">{totals.upcoming}</div>
                        </div>
                        <div className="rounded-[24px] border border-white/10 bg-white/10 p-4 backdrop-blur">
                            <div className="text-xs font-black uppercase tracking-[0.22em] text-slate-300">완료 수업</div>
                            <div className="mt-2 text-4xl font-black">{totals.completed}</div>
                        </div>
                        <div className="rounded-[24px] border border-white/10 bg-white/10 p-4 backdrop-blur">
                            <div className="text-xs font-black uppercase tracking-[0.22em] text-slate-300">총 슬롯</div>
                            <div className="mt-2 text-4xl font-black">{totals.total}</div>
                        </div>
                    </div>
                </div>
            </section>

            <div className="grid gap-6 xl:grid-cols-[1.45fr_0.75fr]">
                <section className="space-y-5">
                    {subjects.map((subject) => (
                        <SubjectCard
                            key={subject}
                            subject={subject}
                            payload={timelineData[subject]}
                            markDone={markDone}
                            pullLessonForward={pullLessonForward}
                            extendSchedule={extendSchedule}
                            marking={marking}
                        />
                    ))}
                </section>

                <ActivityPanel historyView={historyView} subjectFilter={subjectFilter} />
            </div>
        </div>
    );
}
