import { useEffect, useMemo, useState } from "react";
import { ActionsView } from "./components/ActionsView";
import { DashboardView } from "./components/DashboardView";
import { LessonListView } from "./components/LessonListView";
import { useScheduleData } from "./hooks/useScheduleData";
import { getSubjectStyle, sortSubjects, subjectMatches } from "./lib/constants";
import { filterItemsBySubject } from "./lib/lessonFields";
import "./index.css";

const TAB_CONFIG = {
    placements: {
        label: "수업 배치",
        eyebrow: "Placement Board",
        title: "오늘, 다음 수업일, 선택한 주와 달의 배치를 함께 봅니다.",
        description: (subjectLabel) =>
            subjectLabel
                ? `${subjectLabel} 과목만 골라 배치와 완료 상태를 확인하고 바로 조정할 수 있습니다.`
                : "완료한 수업은 남겨 두고, 다음 수업일과 주간·월간 배치를 함께 확인합니다.",
    },
    progress: {
        label: "진도 현황",
        eyebrow: "Timeline Board",
        title: "과목별로 어떤 수업이 언제 있는지 흐름 중심으로 보여줍니다.",
        description: (subjectLabel) =>
            subjectLabel
                ? `${subjectLabel} 과목의 다음 수업, 남은 수업, 최근 완료를 중심으로 보여줍니다.`
                : "퍼센트보다 실제 수업 일정과 최근 처리 흐름을 먼저 보도록 구성했습니다.",
    },
    actions: {
        label: "일정 관리",
        eyebrow: "Schedule Control",
        title: "과목 전체 이동과 개별 수업 조정을 한 자리에서 처리합니다.",
        description: (subjectLabel) =>
            subjectLabel
                ? `${subjectLabel} 과목 위주로 전체 이동과 개별 수업 조정을 진행할 수 있습니다.`
                : "개별 수업은 다음 차시 당겨오기·한 차시 더 쓰기 기준으로, 필요하면 교환도 할 수 있습니다.",
    },
};

const numberFormatter = new Intl.NumberFormat("ko-KR");

function formatLastUpdated(lastUpdated) {
    if (!lastUpdated) {
        return "방금 전";
    }

    return new Intl.DateTimeFormat("ko-KR", {
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date(lastUpdated));
}

function SidebarTabButton({ active, label, meta, onClick }) {
    return (
        <button
            className={`flex w-full items-center justify-between rounded-[18px] px-4 py-3 text-left transition ${
                active
                    ? "bg-[#005bbf] text-white shadow-lg shadow-sky-900/15"
                    : "bg-slate-50 text-slate-700 hover:bg-slate-100"
            }`}
            onClick={onClick}
            type="button"
        >
            <span className="text-sm font-bold">{label}</span>
            <span className={`text-[11px] font-bold tracking-[0.18em] ${active ? "text-sky-100" : "text-slate-400"}`}>
                {meta}
            </span>
        </button>
    );
}

function SubjectFilterButton({ active, subject, onClick }) {
    const style = getSubjectStyle(subject);

    return (
        <button
            className={`flex w-full items-center gap-3 rounded-[16px] border px-4 py-3 text-left transition ${
                active
                    ? "border-[#005bbf] bg-[#eff6ff] text-slate-900 shadow-sm"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
            }`}
            onClick={onClick}
            type="button"
        >
            <span
                className={`flex h-10 w-10 items-center justify-center rounded-2xl text-lg ${style.bg}`}
                style={{ color: style.fill }}
            >
                {style.icon}
            </span>
            <span className="min-w-0 flex-1 truncate text-sm font-semibold">{subject}</span>
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: style.fill }} />
        </button>
    );
}

function OverviewCard({ label, value, description }) {
    return (
        <div className="rounded-[24px] border border-white/70 bg-white/75 p-4 shadow-sm backdrop-blur">
            <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">{label}</div>
            <div className="mt-3 text-3xl font-black tracking-tight text-slate-900">{value}</div>
            <div className="mt-2 text-sm leading-5 text-slate-500">{description}</div>
        </div>
    );
}

export default function App() {
    const [activeTab, setActiveTab] = useState("placements");
    const [selectedSubject, setSelectedSubject] = useState(null);
    const {
        views,
        subjects,
        loading,
        error,
        toast,
        lastUpdated,
        isProcessing,
        boardDate,
        setBoardDate,
        loadData,
        markDone,
        pushSchedule,
        extendSchedule,
        pullLessonForward,
        swapLessons,
    } = useScheduleData();

    const viewMap = useMemo(
        () => Object.fromEntries(views.map((view) => [view.id, view])),
        [views],
    );

    const orderedSubjects = useMemo(() => sortSubjects(subjects), [subjects]);
    const filteredSubjects = useMemo(
        () => orderedSubjects.filter((subject) => subjectMatches(subject, selectedSubject)),
        [orderedSubjects, selectedSubject],
    );
    const selectedSubjectLabel = selectedSubject || null;

    useEffect(() => {
        if (selectedSubject && !orderedSubjects.some((subject) => subjectMatches(subject, selectedSubject))) {
            setSelectedSubject(null);
        }
    }, [orderedSubjects, selectedSubject]);

    const todayCount = filterItemsBySubject(viewMap.today?.data, selectedSubject).length;
    const nextSchoolDayCount = filterItemsBySubject(viewMap.next_school_day?.data, selectedSubject).length;
    const thisWeekCount = filterItemsBySubject(viewMap.thisweek?.data, selectedSubject).length;
    const thisMonthCount = filterItemsBySubject(viewMap.thismonth?.data, selectedSubject).length;
    const agendaItems = filterItemsBySubject(viewMap.agenda?.data, selectedSubject);

    const timelineData = viewMap.subject_timeline?.data || {};
    const timelineSubjects = Object.keys(timelineData).filter((subject) => subjectMatches(subject, selectedSubject));
    const timelineTotals = timelineSubjects.reduce(
        (accumulator, subject) => {
            const payload = timelineData[subject] || {};
            accumulator.total += payload.total_count || 0;
            accumulator.completed += payload.completed_count || 0;
            accumulator.upcoming += (payload.upcoming || []).length;
            return accumulator;
        },
        { total: 0, completed: 0, upcoming: 0 },
    );

    const tabs = [
        {
            id: "placements",
            label: TAB_CONFIG.placements.label,
            meta: `${todayCount + nextSchoolDayCount} BOARD`,
        },
        {
            id: "progress",
            label: TAB_CONFIG.progress.label,
            meta: `${timelineTotals.upcoming} UPCOMING`,
        },
        {
            id: "actions",
            label: TAB_CONFIG.actions.label,
            meta: `${agendaItems.length} ACTIONS`,
        },
    ];

    const headerStats = [
        { label: "오늘", value: numberFormatter.format(todayCount) },
        { label: "다음 수업일", value: numberFormatter.format(nextSchoolDayCount) },
        { label: "예정 슬롯", value: numberFormatter.format(agendaItems.length) },
    ];

    const heroCards = useMemo(() => {
        if (activeTab === "progress") {
            return [
                {
                    label: "남은 수업",
                    value: numberFormatter.format(timelineTotals.upcoming),
                    description: "앞으로 배치된 예정 수업",
                },
                {
                    label: "완료 수업",
                    value: numberFormatter.format(timelineTotals.completed),
                    description: "기록에 남아 있는 완료 슬롯",
                },
                {
                    label: "표시 과목",
                    value: numberFormatter.format(timelineSubjects.length),
                    description: selectedSubjectLabel ? `${selectedSubjectLabel} 필터 적용 중` : "현재 표시 중인 과목 수",
                },
            ];
        }

        if (activeTab === "actions") {
            return [
                {
                    label: "조정 가능 슬롯",
                    value: numberFormatter.format(agendaItems.length),
                    description: "빠른 조정이 가능한 예정 수업",
                },
                {
                    label: "관리 과목",
                    value: numberFormatter.format(filteredSubjects.length || orderedSubjects.length),
                    description: selectedSubjectLabel ? `${selectedSubjectLabel} 중심 보기` : "전체 과목 기준",
                },
                {
                    label: "선택 주 수업",
                    value: numberFormatter.format(thisWeekCount),
                    description: "선택한 주에 잡힌 모든 수업",
                },
            ];
        }

        return [
            {
                label: "오늘 수업",
                value: numberFormatter.format(todayCount),
                description: selectedSubjectLabel ? `${selectedSubjectLabel} 기준` : "오늘 표시되는 수업 수",
            },
            {
                label: "다음 수업일",
                value: numberFormatter.format(nextSchoolDayCount),
                description: "다음으로 수업이 잡힌 날짜의 슬롯 수",
            },
            {
                label: "선택 달 수업",
                value: numberFormatter.format(thisMonthCount),
                description: "현재 선택한 달에 잡힌 수업 수",
            },
        ];
    }, [
        activeTab,
        agendaItems.length,
        filteredSubjects.length,
        orderedSubjects.length,
        selectedSubjectLabel,
        thisMonthCount,
        thisWeekCount,
        timelineSubjects.length,
        timelineTotals.completed,
        timelineTotals.upcoming,
        todayCount,
        nextSchoolDayCount,
    ]);

    const currentTab = TAB_CONFIG[activeTab];

    function renderActiveView() {
        if (activeTab === "progress") {
            return (
                <DashboardView
                    views={views}
                    markDone={markDone}
                    pullLessonForward={pullLessonForward}
                    extendSchedule={extendSchedule}
                    marking={isProcessing}
                    subjectFilter={selectedSubject}
                />
            );
        }

        if (activeTab === "actions") {
            return (
                <ActionsView
                    subjects={orderedSubjects}
                    agendaItems={viewMap.agenda?.data || []}
                    pushSchedule={pushSchedule}
                    extendSchedule={extendSchedule}
                    pullLessonForward={pullLessonForward}
                    swapLessons={swapLessons}
                    isProcessing={isProcessing}
                    subjectFilter={selectedSubject}
                />
            );
        }

        return (
            <LessonListView
                views={views}
                markDone={markDone}
                pullLessonForward={pullLessonForward}
                extendSchedule={extendSchedule}
                marking={isProcessing}
                subjectFilter={selectedSubject}
                boardDate={boardDate}
                setBoardDate={setBoardDate}
            />
        );
    }

    return (
        <div className="min-h-screen bg-[radial-gradient(circle_at_top,#fbfdff_0%,#eef4fb_46%,#e7eef7_100%)] text-slate-900">
            <header className="border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
                <div className="mx-auto max-w-[1600px] px-4 py-5 sm:px-6 lg:px-8">
                    <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
                        <div className="space-y-3">
                            <div className="inline-flex items-center gap-2 rounded-full border border-sky-100 bg-sky-50/70 px-3 py-1 text-[11px] font-black tracking-[0.24em] text-sky-700">
                                <span className="h-2 w-2 rounded-full bg-sky-500" />
                                TEACHER SCHEDULE
                            </div>
                            <div>
                                <h1 className="text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">
                                    교사 수업 일정
                                </h1>
                                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                                    수업 배치, 진도 흐름, 일정 조정을 한 화면 구조 안에서 오가며 처리할 수 있도록 정리했습니다.
                                </p>
                            </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-3">
                            {headerStats.map((stat) => (
                                <div
                                    key={stat.label}
                                    className="rounded-[22px] border border-slate-200 bg-white/80 px-4 py-3 shadow-sm"
                                >
                                    <div className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">
                                        {stat.label}
                                    </div>
                                    <div className="mt-1 text-xl font-black text-slate-900">{stat.value}</div>
                                </div>
                            ))}
                            <button
                                className="inline-flex min-w-[140px] items-center justify-center rounded-[18px] border border-slate-200 bg-slate-950 px-4 py-3 text-sm font-bold text-white transition hover:-translate-y-0.5 hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
                                onClick={loadData}
                                disabled={loading}
                                type="button"
                            >
                                {loading ? "불러오는 중..." : "새로고침"}
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            <div className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
                <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
                    <aside className="hidden lg:block">
                        <div className="shell-card sticky top-6 p-4">
                            <div className="px-3 pt-2">
                                <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">
                                    Menu
                                </div>
                            </div>
                            <div className="mt-4 space-y-2">
                                {tabs.map((tab) => (
                                    <SidebarTabButton
                                        key={tab.id}
                                        active={activeTab === tab.id}
                                        label={tab.label}
                                        meta={tab.meta}
                                        onClick={() => setActiveTab(tab.id)}
                                    />
                                ))}
                            </div>

                            <div className="my-6 border-t border-slate-200" />

                            <div className="px-3">
                                <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">
                                    Subject Filter
                                </div>
                                <p className="mt-2 text-sm leading-5 text-slate-500">
                                    과목을 고르면 배치, 진도, 일정 관리 화면이 모두 같은 기준으로 좁혀집니다.
                                </p>
                            </div>

                            <div className="mt-4 space-y-2">
                                <button
                                    className={`w-full rounded-[16px] px-4 py-3 text-left text-sm font-bold transition ${
                                        selectedSubject === null
                                            ? "bg-slate-950 text-white"
                                            : "bg-slate-50 text-slate-700 hover:bg-slate-100"
                                    }`}
                                    onClick={() => setSelectedSubject(null)}
                                    type="button"
                                >
                                    전체 과목
                                </button>
                                {orderedSubjects.map((subject) => (
                                    <SubjectFilterButton
                                        key={subject}
                                        active={subjectMatches(subject, selectedSubject)}
                                        subject={subject}
                                        onClick={() => setSelectedSubject(subject)}
                                    />
                                ))}
                            </div>

                            <div className="mt-6 rounded-[24px] border border-sky-100 bg-[linear-gradient(145deg,#f0f9ff_0%,#eff6ff_100%)] p-4">
                                <div className="text-[11px] font-black uppercase tracking-[0.22em] text-sky-600">
                                    Quick Note
                                </div>
                                <div className="mt-3 text-lg font-black text-slate-900">
                                    {selectedSubjectLabel ? `${selectedSubjectLabel} 집중 보기` : "전체 과목 보기"}
                                </div>
                                <p className="mt-2 text-sm leading-6 text-slate-600">
                                    {selectedSubjectLabel
                                        ? `${selectedSubjectLabel} 관련 수업만 보고 있습니다. 다른 과목은 사이드바에서 바로 전환할 수 있습니다.`
                                        : "PDF 보기, 완료 처리, 다음 차시 당겨오기, 교환, 연장까지 이 화면에서 바로 이어서 할 수 있습니다."}
                                </p>
                                <div className="mt-4 rounded-2xl border border-white/70 bg-white/70 px-4 py-3 text-sm font-semibold text-slate-600">
                                    마지막 동기화 {formatLastUpdated(lastUpdated)}
                                </div>
                            </div>
                        </div>
                    </aside>

                    <main className="min-w-0 space-y-5">
                        <div className="space-y-3 lg:hidden">
                            <div className="hide-scrollbar flex gap-2 overflow-x-auto pb-1">
                                {tabs.map((tab) => (
                                    <button
                                        key={tab.id}
                                        className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-bold transition ${
                                            activeTab === tab.id
                                                ? "bg-slate-950 text-white"
                                                : "bg-white text-slate-600 shadow-sm"
                                        }`}
                                        onClick={() => setActiveTab(tab.id)}
                                        type="button"
                                    >
                                        {tab.label}
                                    </button>
                                ))}
                            </div>
                            <div className="hide-scrollbar flex gap-2 overflow-x-auto pb-1">
                                <button
                                    className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold transition ${
                                        selectedSubject === null
                                            ? "bg-[#005bbf] text-white"
                                            : "bg-white text-slate-600 shadow-sm"
                                    }`}
                                    onClick={() => setSelectedSubject(null)}
                                    type="button"
                                >
                                    전체 과목
                                </button>
                                {orderedSubjects.map((subject) => {
                                    const style = getSubjectStyle(subject);
                                    return (
                                        <button
                                            key={subject}
                                            className={`inline-flex items-center gap-2 whitespace-nowrap rounded-full border px-4 py-2 text-sm font-semibold transition ${
                                                subjectMatches(subject, selectedSubject)
                                                    ? "border-[#005bbf] bg-[#eff6ff] text-slate-900"
                                                    : "border-transparent bg-white text-slate-600 shadow-sm"
                                            }`}
                                            onClick={() => setSelectedSubject(subject)}
                                            type="button"
                                        >
                                            <span>{style.icon}</span>
                                            <span>{subject}</span>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        {error && (
                            <div className="rounded-[24px] border border-red-200 bg-red-50 px-5 py-4 text-sm font-semibold text-red-700 shadow-sm">
                                {error}
                            </div>
                        )}

                        <section className="shell-card soft-grid p-6 sm:p-8">
                            <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr] xl:items-end">
                                <div>
                                    <div className="text-[11px] font-black uppercase tracking-[0.28em] text-sky-700">
                                        {currentTab.eyebrow}
                                    </div>
                                    <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-950">
                                        {currentTab.title}
                                    </h2>
                                    <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
                                        {currentTab.description(selectedSubjectLabel)}
                                    </p>
                                    <div className="mt-4 inline-flex flex-wrap items-center gap-2 rounded-full border border-white/80 bg-white/75 px-3 py-2 text-sm font-semibold text-slate-600 shadow-sm">
                                        <span className="text-slate-400">현재 기준</span>
                                        <span className="text-slate-900">{selectedSubjectLabel || "전체 과목"}</span>
                                        <span className="text-slate-300">/</span>
                                        <span>{formatLastUpdated(lastUpdated)}</span>
                                    </div>
                                </div>

                                <div className="grid gap-3 sm:grid-cols-3">
                                    {heroCards.map((card) => (
                                        <OverviewCard
                                            key={card.label}
                                            label={card.label}
                                            value={card.value}
                                            description={card.description}
                                        />
                                    ))}
                                </div>
                            </div>
                        </section>

                        {loading && views.length === 0 ? (
                            <div className="shell-card flex min-h-[42vh] flex-col items-center justify-center px-6 py-12 text-center">
                                <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900" />
                                <p className="mt-4 text-sm font-semibold text-slate-500">
                                    수업 데이터를 불러오는 중입니다.
                                </p>
                            </div>
                        ) : (
                            renderActiveView()
                        )}
                    </main>
                </div>
            </div>

            {toast && (
                <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 animate-in fade-in slide-in-from-bottom-5 duration-300">
                    <div
                        className={`rounded-full px-5 py-3 text-sm font-bold shadow-lg ${
                            toast.type === "error"
                                ? "bg-red-600 text-white shadow-red-600/25"
                                : "bg-slate-950 text-white shadow-slate-950/20"
                        }`}
                    >
                        {toast.msg}
                    </div>
                </div>
            )}
        </div>
    );
}
