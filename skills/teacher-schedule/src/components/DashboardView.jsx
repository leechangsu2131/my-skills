import { getSubjectStyle } from "../lib/constants";

export function OverallProgress({ views }) {
    const progView = views.find(v => v.id === "progress");
    if (!progView || !progView.data) return null;

    let totalClasses = 0;
    let totalDone = 0;
    Object.values(progView.data).forEach(p => {
        totalClasses += p.전체;
        totalDone += p.완료;
    });
    const percentage = totalClasses === 0 ? 0 : Math.round((totalDone / totalClasses) * 100);

    return (
        <div className="bg-gradient-to-br from-indigo-900 to-indigo-700 rounded-2xl p-6 shadow-xl text-white mb-8 border border-indigo-800/50">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-xl font-bold opacity-90">전체 학기 진도율</h2>
                    <p className="text-sm text-indigo-200 mt-1">모든 과목 통합 기준</p>
                </div>
                <div className="text-5xl font-extrabold tracking-tight">
                    {percentage}<span className="text-2xl text-white/70">%</span>
                </div>
            </div>
            <div className="h-4 bg-white/20 rounded-full overflow-hidden mb-3">
                <div
                    className="h-full bg-gradient-to-r from-emerald-400 to-emerald-500 rounded-full transition-all duration-1000 ease-out"
                    style={{ width: `${percentage}%` }}
                />
            </div>
            <div className="flex justify-between text-sm font-medium text-white/80">
                <span>총 {totalClasses}차시 중 {totalDone}차시 완료</span>
                <span>{totalClasses - totalDone}차시 남음</span>
            </div>
        </div>
    );
}

function UnitProgress({ unitData, style }) {
    if (!unitData || unitData.length === 0) return null;
    return (
        <div className="mt-5 space-y-3 border-t border-gray-100 pt-4">
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest pl-1">단원 상세 진도</h4>
            <div className="space-y-2">
                {unitData.map((unit, idx) => {
                    const isFullyDone = unit.percentage === 100;
                    return (
                        <div key={idx} className={`rounded-lg p-2.5 border transition-colors ${isFullyDone ? 'bg-gray-50 border-transparent' : 'bg-white border-gray-100 shadow-sm'}`}>
                            <div className="flex justify-between items-center mb-2">
                                <span className={`text-xs font-bold truncate pr-2 ${isFullyDone ? 'text-gray-400' : 'text-gray-800'}`}>{unit.name}</span>
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${isFullyDone ? 'bg-gray-100 border-gray-200 text-gray-500' : `${style.bg} ${style.border} ${style.accent}`}`}>{unit.percentage}%</span>
                            </div>
                            <div className="flex gap-0.5 h-1.5 w-full">
                                {unit.lessons.map((l, i) => (
                                    <div
                                        key={i}
                                        className={`flex-1 rounded-sm transition-colors ${l.실행여부 ? (isFullyDone ? 'bg-gray-300' : style.accent.replace('text-', 'bg-')) : 'bg-gray-100'}`}
                                        title={`${l.차시}차시: ${l.수업내용}`}
                                    ></div>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export function DashboardView({ views, markDone, marking }) {
    const nextView = views.find(v => v.id === "next");
    const progView = views.find(v => v.id === "progress");
    const unitView = views.find(v => v.id === "unit_progress");

    if (!nextView || !progView) return <div className="text-center py-12 text-gray-500">데이터가 없습니다.</div>;

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <OverallProgress views={views} />

            <h3 className="text-lg font-bold text-gray-900 mb-4 px-1">오늘 & 다음 수업</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {Object.keys(nextView.data).map(sub => {
                    const data = nextView.data[sub];
                    const prog = progView.data[sub];
                    const unitData = unitView?.data?.[sub];
                    const style = getSubjectStyle(sub);
                    const nextCls = data?.next;

                    if (!nextCls && prog?.완료 === prog?.전체) return null;

                    return (
                        <div key={sub} className="card border-t-4 flex flex-col" style={{ borderTopColor: 'currentColor' }}>
                            <div className="flex justify-between items-center mb-4">
                                <div className="flex items-center gap-2">
                                    <span className="text-2xl">{style.icon}</span>
                                    <span className={`text-lg font-bold ${style.accent}`}>{sub}</span>
                                </div>
                                <span className={`text-sm font-bold px-3 py-1 rounded-full ${style.bg} ${style.accent}`}>
                                    {prog ? prog.진도율 : "0%"}
                                </span>
                            </div>

                            {prog && (
                                <div className="h-2 bg-gray-100 rounded-full overflow-hidden mb-5">
                                    <div
                                        className={`h-full ${style.bg.replace('50', '500')} opacity-80 transition-all duration-700`}
                                        style={{ width: prog.진도율 }}
                                    />
                                </div>
                            )}

                            {nextCls ? (
                                <div className="bg-gray-50 rounded-lg p-4 border border-gray-100 shadow-inner">
                                    <span className="inline-block text-[10px] font-black tracking-wider text-red-500 bg-red-100 px-2 py-0.5 rounded flex-none mb-2">NOW</span>
                                    <div className="text-sm font-semibold text-gray-900 leading-snug mb-3 hover:text-indigo-600 transition-colors cursor-default">
                                        {nextCls.수업내용}
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-xs font-medium text-gray-500 bg-white px-2 py-1 rounded shadow-sm border border-gray-200">
                                            {nextCls.차시}차시
                                        </span>
                                        <button
                                            className={`text-xs font-bold text-white px-3 py-1.5 rounded-md shadow-sm transition-transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed`}
                                            style={{ backgroundColor: 'currentColor' }}
                                            onClick={() => markDone(nextCls)}
                                            disabled={marking === (nextCls._row || nextCls.행번호)}
                                        >
                                            {marking === (nextCls._row || nextCls.행번호) ? "..." : "완료 ✓"}
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="text-center py-4 bg-gray-50 rounded-lg border border-dashed border-gray-200 text-sm font-semibold text-gray-400">
                                    모든 진도 완료! 🎉
                                </div>
                            )}

                            {unitData && <UnitProgress unitData={unitData} style={style} />}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
