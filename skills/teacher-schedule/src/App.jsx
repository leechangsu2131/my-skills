import { useState } from "react";
import { useScheduleData } from "./hooks/useScheduleData";
import { DashboardView } from "./components/DashboardView";
import { LessonListView } from "./components/LessonListView";
import { ActionsView } from "./components/ActionsView";
import "./index.css";

export default function App() {
    const [activeTab, setActiveTab] = useState("dashboard");
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
        extendSchedule
    } = useScheduleData();

    return (
        <div className="min-h-screen bg-gray-50 text-gray-900 font-sans selection:bg-indigo-100">
            <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200 pt-6">
                <div className="max-w-4xl mx-auto px-6 flex justify-between items-center mb-6">
                    <div className="flex items-center gap-3">
                        <span className="text-3xl filter drop-shadow-sm">📚</span>
                        <div>
                            <h1 className="text-2xl font-extrabold tracking-tight text-gray-900">스마트 진도표</h1>
                            <p className="text-xs font-bold text-indigo-500 uppercase tracking-widest mt-0.5">Teacher Schedule Pro</p>
                        </div>
                    </div>
                    <button
                        className="w-10 h-10 flex items-center justify-center bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-xl transition-colors disabled:opacity-50"
                        onClick={loadData}
                        disabled={loading}
                        title="새로고침"
                    >
                        {loading ? <span className="animate-spin text-xl">↻</span> : <span className="text-xl">⟳</span>}
                    </button>
                </div>

                <div className="max-w-4xl mx-auto px-6 flex gap-6">
                    {[
                        { id: 'dashboard', label: '대시보드' },
                        { id: 'lesson_list', label: '수업 목록' },
                        { id: 'actions', label: '일정 관리' }
                    ].map(tab => (
                        <button
                            key={tab.id}
                            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(tab.id)}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-6 py-8">
                {error && (
                    <div className="bg-red-50 text-red-600 rounded-lg p-4 mb-6 text-sm font-medium border border-red-200">
                        {error}
                    </div>
                )}

                {loading && views.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                        <div className="animate-spin text-4xl text-indigo-500 mb-4">⟳</div>
                        <p className="font-medium text-sm">데이터 연동 중...</p>
                    </div>
                ) : (
                    <>
                        {activeTab === 'dashboard' && <DashboardView views={views} markDone={markDone} marking={isProcessing} />}
                        {activeTab === 'lesson_list' && <LessonListView views={views} markDone={markDone} marking={isProcessing} />}
                        {activeTab === 'actions' && <ActionsView subjects={subjects} pushSchedule={pushSchedule} extendSchedule={extendSchedule} isProcessing={isProcessing} />}
                    </>
                )}
            </main>

            {/* Toast Notification */}
            {toast && (
                <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50 animate-in slide-in-from-bottom-5 fade-in duration-300">
                    <div className={`px-6 py-3 rounded-full shadow-lg font-bold text-sm ${toast.type === "error" ? "bg-red-500 text-white shadow-red-500/20" : "bg-gray-900 text-white shadow-gray-900/20"
                        }`}>
                        {toast.msg}
                    </div>
                </div>
            )}
        </div>
    );
}
