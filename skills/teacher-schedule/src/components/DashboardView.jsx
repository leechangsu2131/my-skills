import { getSubjectStyle } from "../lib/constants";

const PDF_BASE = "http://127.0.0.1:5000/api/pdf";

function getRecordKey(item) {
    return item?.lesson_id || item?._record_key || item?._row || "";
}

function getActionKey(item) {
    return item?._bridge_row || getRecordKey(item);
}

function getTitle(item) {
    return item?.["수업내용"] || item?.title || "제목 없음";
}

function getUnit(item) {
    return item?.["대단원"] || item?.unit || "";
}

function getLesson(item) {
    return item?.["차시"] || item?.lesson || "";
}

function getPlannedDate(item) {
    return item?.["계획일"] || item?.slot_date || "";
}

function getPlannedPeriod(item) {
    return item?.["계획교시"] || item?.slot_period || "";
}

function getPdfPath(item) {
    return item?.["pdf파일"] || item?.pdf_file || "";
}

function formatSchedule(item) {
    const plannedDate = getPlannedDate(item);
    const plannedPeriod = getPlannedPeriod(item);
    if (plannedDate && plannedPeriod) {
        return `${plannedDate} · ${plannedPeriod}교시`;
    }
    if (plannedDate) {
        return plannedDate;
    }
    if (plannedPeriod) {
        return `${plannedPeriod}교시`;
    }
    return "계획 미정";
}

function ProgressHero({ progressView }) {
    const entries = Object.values(progressView?.data || {});
    const totalLessons = entries.reduce((sum, item) => sum + Number(item?.["전체"] || 0), 0);
    const doneLessons = entries.reduce((sum, item) => sum + Number(item?.["완료"] || 0), 0);
    const percentage = totalLessons === 0 ? 0 : Math.round((doneLessons / totalLessons) * 100);

    return (
        <section className="rounded-[32px] border border-stone-200 bg-[linear-gradient(135deg,#1c1917_0%,#44403c_55%,#78716c_100%)] p-6 text-white shadow-xl shadow-stone-900/10">
            <div className="grid gap-6 lg:grid-cols-[1.3fr_0.9fr] lg:items-end">
                <div>
                    <div className="text-[11px] font-bold uppercase tracking-[0.28em] text-stone-300">
                        Progress Board
                    </div>
                    <h2 className="mt-3 text-3xl font-black tracking-tight">
                        진도 흐름을 과목별로 확인합니다.
                    </h2>
                    <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-200">
                        여기서는 무엇을 얼마나 진행했는지와 다음 차시가 어디에 놓여 있는지를 봅니다.
                        실제 날짜와 교시는 수업배치 탭에서 다룹니다.
                    </p>
                </div>

                <div className="rounded-[28px] border border-white/10 bg-white/10 p-5 backdrop-blur">
                    <div className="flex items-end justify-between gap-4">
                        <div>
                            <div className="text-xs font-bold uppercase tracking-[0.22em] text-stone-300">
                                Completion
                            </div>
                            <div className="mt-2 text-5xl font-black tracking-tight">
                                {percentage}
                                <span className="ml-1 text-2xl text-stone-300">%</span>
                            </div>
                        </div>
                        <div className="text-right text-sm text-stone-200">
                            <div>{doneLessons}차시 완료</div>
                            <div>{Math.max(totalLessons - doneLessons, 0)}차시 남음</div>
                        </div>
                    </div>
                    <div className="mt-5 h-3 overflow-hidden rounded-full bg-white/15">
                        <div
                            className="h-full rounded-full bg-[linear-gradient(90deg,#fde68a_0%,#f97316_100%)]"
                            style={{ width: `${percentage}%` }}
                        />
                    </div>
                </div>
            </div>
        </section>
    );
}

function ActivityPanel({ historyView }) {
    const logs = historyView?.data || [];
    if (logs.length === 0) {
        return (
            <section className="rounded-[28px] border border-stone-200 bg-white/85 p-5 shadow-sm">
                <div className="text-sm font-bold text-stone-900">최근 활동</div>
                <p className="mt-3 text-sm text-stone-500">기록된 활동이 아직 없습니다.</p>
            </section>
        );
    }

    return (
        <section className="rounded-[28px] border border-stone-200 bg-white/85 p-5 shadow-sm">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-black tracking-[0.2em] text-stone-400">RECENT ACTIVITY</h3>
                <span className="rounded-full bg-stone-100 px-3 py-1 text-xs font-bold text-stone-500">
                    {logs.length}건
                </span>
            </div>
            <div className="mt-5 space-y-4">
                {logs.slice(0, 6).map((log, index) => (
                    <div key={`${log.timestamp}-${index}`} className="flex gap-3">
                        <div className="mt-1 h-2.5 w-2.5 rounded-full bg-amber-500" />
                        <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-3">
                                <div className="truncate text-sm font-bold text-stone-900">
                                    {log.subject || "과목 미지정"}
                                </div>
                                <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-stone-400">
                                    {log.action}
                                </div>
                            </div>
                            <div className="mt-1 text-sm text-stone-500">{log.details}</div>
                            <div className="mt-1 text-xs text-stone-400">
                                {new Date(log.timestamp).toLocaleString("ko-KR")}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
}

function UnitMeters({ unitData, style }) {
    if (!Array.isArray(unitData) || unitData.length === 0) {
        return null;
    }

    return (
        <div className="mt-5 border-t border-stone-100 pt-4">
            <div className="mb-3 text-[11px] font-bold uppercase tracking-[0.24em] text-stone-400">
                Unit Progress
            </div>
            <div className="space-y-3">
                {unitData.map((unit) => (
                    <div key={unit.name} className="rounded-2xl border border-stone-100 bg-stone-50/70 p-3">
                        <div className="flex items-center justify-between gap-3">
                            <div className="truncate text-sm font-semibold text-stone-700">{unit.name}</div>
                            <div className={`rounded-full px-2 py-1 text-[11px] font-bold ${style.bg} ${style.accent}`}>
                                {unit.completed}/{unit.total}
                            </div>
                        </div>
                        <div className="mt-3 flex gap-1">
                            {unit.lessons.map((lesson, index) => (
                                <div
                                    key={`${unit.name}-${index}`}
                                    className="h-2 flex-1 rounded-full bg-stone-200"
                                    style={lesson?.["실행여부"] ? { backgroundColor: style.fill } : undefined}
                                    title={`${lesson?.["차시"] || ""}차시 ${lesson?.["수업내용"] || ""}`}
                                />
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function SubjectCard({ subject, payload, progress, unitData, markDone, marking }) {
    const style = getSubjectStyle(subject);
    const nextItem = payload?.next || null;
    const recentItem = payload?.recent || null;
    const actionKey = getActionKey(nextItem);
    const recordKey = getRecordKey(nextItem);
    const isProcessing = Boolean(nextItem) && marking === actionKey;
    const progressText = progress?.["진도율"] || "0.0%";
    const completed = Number(progress?.["완료"] || 0);
    const total = Number(progress?.["전체"] || 0);

    return (
        <article className="rounded-[30px] border border-stone-200 bg-white/90 p-5 shadow-sm shadow-stone-200/40">
            <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                    <div className={`flex h-14 w-14 items-center justify-center rounded-2xl text-2xl ${style.bg} ${style.accent}`}>
                        {style.icon}
                    </div>
                    <div>
                        <h3 className={`text-lg font-black ${style.accent}`}>{subject}</h3>
                        <p className="text-sm text-stone-500">
                            {completed}/{total}차시 완료
                        </p>
                    </div>
                </div>
                <div className={`rounded-full px-3 py-1 text-xs font-bold ${style.bg} ${style.accent}`}>
                    {progressText}
                </div>
            </div>

            <div className="mt-4 h-2 overflow-hidden rounded-full bg-stone-100">
                <div
                    className="h-full rounded-full"
                    style={{ width: progressText, backgroundColor: style.fill }}
                />
            </div>

            <div className="mt-5 rounded-[24px] border border-stone-100 bg-stone-50/80 p-4">
                <div className="flex items-center justify-between gap-3">
                    <div className="text-xs font-bold uppercase tracking-[0.22em] text-stone-400">
                        다음 수업
                    </div>
                    {nextItem && (
                        <div className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-stone-500 shadow-sm">
                            {formatSchedule(nextItem)}
                        </div>
                    )}
                </div>

                {nextItem ? (
                    <>
                        <div className="mt-3 text-lg font-bold leading-snug text-stone-900">
                            {getTitle(nextItem)}
                        </div>
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-stone-500">
                            <span className="rounded-full bg-white px-3 py-1 shadow-sm">
                                {getLesson(nextItem)}차시
                            </span>
                            {getUnit(nextItem) && (
                                <span className="rounded-full bg-white px-3 py-1 shadow-sm">
                                    {getUnit(nextItem)}
                                </span>
                            )}
                        </div>
                        <div className="mt-4 flex flex-wrap gap-2">
                            {getPdfPath(nextItem) && (
                                <a
                                    href={`${PDF_BASE}/${encodeURIComponent(recordKey)}`}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-flex items-center justify-center rounded-2xl border border-stone-200 bg-white px-4 py-2 text-sm font-bold text-stone-700 transition hover:bg-stone-50"
                                >
                                    PDF 보기
                                </a>
                            )}
                            <button
                                className={`inline-flex items-center justify-center rounded-2xl px-4 py-2 text-sm font-bold text-white transition ${
                                    isProcessing ? "cursor-not-allowed bg-stone-300" : "bg-stone-900 hover:-translate-y-0.5"
                                }`}
                                onClick={() => markDone(nextItem)}
                                disabled={isProcessing}
                            >
                                {isProcessing ? "처리 중..." : "이 수업 완료"}
                            </button>
                        </div>
                    </>
                ) : (
                    <div className="mt-3 rounded-2xl border border-dashed border-stone-200 bg-white px-4 py-6 text-center text-sm font-semibold text-stone-400">
                        배치된 다음 수업이 없습니다.
                    </div>
                )}
            </div>

            {recentItem && (
                <div className="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    <span className="font-bold">최근 완료:</span> {getTitle(recentItem)}
                </div>
            )}

            <UnitMeters unitData={unitData} style={style} />
        </article>
    );
}

export function DashboardView({ views, markDone, marking }) {
    const progressView = views.find((view) => view.id === "progress");
    const nextView = views.find((view) => view.id === "next");
    const unitView = views.find((view) => view.id === "unit_progress");
    const historyView = views.find((view) => view.id === "history");

    if (!progressView || !nextView) {
        return (
            <div className="rounded-[28px] border border-stone-200 bg-white p-8 text-center text-stone-500 shadow-sm">
                진도 데이터를 찾지 못했습니다.
            </div>
        );
    }

    const subjects = Object.keys(nextView.data || {});

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <ProgressHero progressView={progressView} />

            <div className="grid gap-6 xl:grid-cols-[1.45fr_0.75fr]">
                <section className="space-y-5">
                    {subjects.map((subject) => (
                        <SubjectCard
                            key={subject}
                            subject={subject}
                            payload={nextView.data[subject]}
                            progress={progressView.data?.[subject]}
                            unitData={unitView?.data?.[subject]}
                            markDone={markDone}
                            marking={marking}
                        />
                    ))}
                </section>

                <ActivityPanel historyView={historyView} />
            </div>
        </div>
    );
}
