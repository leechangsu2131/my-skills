import { useState } from "react";
import { useScheduleData } from "./hooks/useScheduleData";
import { DashboardView } from "./components/DashboardView";
import { LessonListView } from "./components/LessonListView";
import { ActionsView } from "./components/ActionsView";
import "./index.css";

function getLessonCount(view) {
    return Array.isArray(view?.data) ? view.data.length : 0;
}

export default function App() {
    const [activeTab, setActiveTab] = useState("placements");
    const {
        views,
        subjects,
        loading,
        error,
        toast,
        isProcessing,
        loadData,
        markDone,
        pushSchedule,
        extendSchedule,
    } = useScheduleData();

    const todayView = views.find((view) => view.id === "today");
    const tomorrowView = views.find((view) => view.id === "tomorrow");
    const progressView = views.find((view) => view.id === "progress");

    const totalLessons = Object.values(progressView?.data || {}).reduce(
        (sum, item) => sum + Number(item?.["전체"] || 0),
        0,
    );
    const doneLessons = Object.values(progressView?.data || {}).reduce(
        (sum, item) => sum + Number(item?.["완료"] || 0),
        0,
    );

    const tabs = [
        {
            id: "placements",
            label: "수업배치",
            meta: `오늘 ${getLessonCount(todayView)}개`,
        },
        {
            id: "progress",
            label: "진도표",
            meta: `${doneLessons}/${totalLessons}`,
        },
        {
            id: "actions",
            label: "관리",
            meta: `${subjects.length}과목`,
        },
    ];

    return (
        <div className="min-h-screen bg-[linear-gradient(180deg,#f6f3ea_0%,#f7fafc_32%,#ffffff_100%)] text-gray-900">
            <header className="sticky top-0 z-40 border-b border-stone-200/70 bg-[#faf7f0]/90 backdrop-blur-xl">
                <div className="mx-auto max-w-6xl px-5 py-5 sm:px-6">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                        <div className="space-y-3">
                            <div className="inline-flex items-center gap-2 rounded-full border border-stone-300 bg-white/80 px-3 py-1 text-[11px] font-bold tracking-[0.24em] text-stone-500">
                                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                                BRIDGE SCHEDULE
                            </div>
                            <div>
                                <h1 className="text-3xl font-black tracking-tight text-stone-900 sm:text-4xl">
                                    교사 스케줄
                                </h1>
                                <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">
                                    진도표는 무엇을 가르칠지, 수업배치는 언제 가르칠지를 보여줍니다.
                                    이제 화면도 그 기준에 맞춰 나누어 봅니다.
                                </p>
                            </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-3">
                            <div className="rounded-2xl border border-stone-200 bg-white/80 px-4 py-3 shadow-sm">
                                <div className="text-[11px] font-bold uppercase tracking-[0.24em] text-stone-400">
                                    Today
                                </div>
                                <div className="mt-1 text-lg font-black text-stone-900">
                                    {getLessonCount(todayView)}
                                </div>
                            </div>
                            <div className="rounded-2xl border border-stone-200 bg-white/80 px-4 py-3 shadow-sm">
                                <div className="text-[11px] font-bold uppercase tracking-[0.24em] text-stone-400">
                                    Tomorrow
                                </div>
                                <div className="mt-1 text-lg font-black text-stone-900">
                                    {getLessonCount(tomorrowView)}
                                </div>
                            </div>
                            <div className="rounded-2xl border border-stone-200 bg-white/80 px-4 py-3 shadow-sm">
                                <div className="text-[11px] font-bold uppercase tracking-[0.24em] text-stone-400">
                                    Progress
                                </div>
                                <div className="mt-1 text-lg font-black text-stone-900">
                                    {doneLessons}/{totalLessons}
                                </div>
                            </div>
                            <button
                                className="inline-flex h-12 items-center justify-center rounded-2xl border border-stone-200 bg-white px-4 text-sm font-bold text-stone-700 shadow-sm transition hover:-translate-y-0.5 hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-50"
                                onClick={loadData}
                                disabled={loading}
                                title="새로고침"
                            >
                                {loading ? "불러오는 중..." : "새로고침"}
                            </button>
                        </div>
                    </div>

                    <div className="mt-5 flex flex-wrap gap-2 rounded-[28px] border border-stone-200 bg-white/70 p-2 shadow-sm">
                        {tabs.map((tab) => {
                            const active = activeTab === tab.id;
                            return (
                                <button
                                    key={tab.id}
                                    className={`flex min-w-[132px] flex-1 items-center justify-between rounded-2xl px-4 py-3 text-left transition ${
                                        active
                                            ? "bg-stone-900 text-white shadow-lg shadow-stone-900/10"
                                            : "text-stone-500 hover:bg-stone-100/80 hover:text-stone-900"
                                    }`}
                                    onClick={() => setActiveTab(tab.id)}
                                >
                                    <span className="text-sm font-bold">{tab.label}</span>
                                    <span
                                        className={`text-[11px] font-bold tracking-[0.18em] ${
                                            active ? "text-stone-300" : "text-stone-400"
                                        }`}
                                    >
                                        {tab.meta}
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                </div>
            </header>

            <main className="mx-auto max-w-6xl px-5 py-8 sm:px-6">
                {error && (
                    <div className="mb-6 rounded-3xl border border-red-200 bg-red-50 px-5 py-4 text-sm font-medium text-red-700 shadow-sm">
                        {error}
                    </div>
                )}

                {loading && views.length === 0 ? (
                    <div className="flex min-h-[40vh] flex-col items-center justify-center rounded-[32px] border border-stone-200 bg-white/80 px-6 text-center shadow-sm">
                        <div className="h-12 w-12 animate-spin rounded-full border-4 border-stone-200 border-t-stone-900" />
                        <p className="mt-4 text-sm font-semibold text-stone-500">
                            수업 데이터를 불러오는 중입니다.
                        </p>
                    </div>
                ) : (
                    <>
                        {activeTab === "placements" && (
                            <LessonListView
                                views={views}
                                markDone={markDone}
                                marking={isProcessing}
                            />
                        )}
                        {activeTab === "progress" && (
                            <DashboardView
                                views={views}
                                markDone={markDone}
                                marking={isProcessing}
                            />
                        )}
                        {activeTab === "actions" && (
                            <ActionsView
                                subjects={subjects}
                                pushSchedule={pushSchedule}
                                extendSchedule={extendSchedule}
                                isProcessing={isProcessing}
                            />
                        )}
                    </>
                )}
            </main>

            {toast && (
                <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 animate-in fade-in slide-in-from-bottom-5 duration-300">
                    <div
                        className={`rounded-full px-5 py-3 text-sm font-bold shadow-lg ${
                            toast.type === "error"
                                ? "bg-red-600 text-white shadow-red-600/20"
                                : "bg-stone-900 text-white shadow-stone-900/20"
                        }`}
                    >
                        {toast.msg}
                    </div>
                </div>
            )}
        </div>
    );
}
