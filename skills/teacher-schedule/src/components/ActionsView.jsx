import { useState } from "react";
import { getSubjectStyle } from "../lib/constants";

export function ActionsView({ subjects, pushSchedule, extendSchedule, isProcessing }) {
    const [pushDays, setPushDays] = useState(7);
    const [pushFrom, setPushFrom] = useState("");

    const daysOptions = [1, 2, 3, 5, 7, 14];

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h3 className="text-lg font-bold text-gray-900 mb-4 px-1">⚙️ 일괄 연기 설정</h3>
            <div className="card mb-8">
                <label className="block text-sm font-bold text-gray-700 mb-3">며칠을 미룰까요?</label>
                <div className="flex flex-wrap gap-2 mb-6">
                    {daysOptions.map(d => (
                        <button
                            key={d}
                            className={`px-4 py-2 text-sm font-bold border rounded-lg transition-all ${pushDays === d
                                    ? 'bg-gray-900 text-white border-gray-900 shadow-md transform scale-105'
                                    : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                                }`}
                            onClick={() => setPushDays(d)}
                        >
                            {d}일
                        </button>
                    ))}
                </div>

                <label className="block text-sm font-bold text-gray-700 mb-2">언제부터 연기할까요? <span className="text-gray-400 font-normal ml-1">(비워두면 전체 일정 연기)</span></label>
                <input
                    type="date"
                    className="w-full max-w-sm px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-gray-900 font-medium focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-shadow outline-none"
                    value={pushFrom}
                    onChange={e => setPushFrom(e.target.value)}
                />
            </div>

            <h3 className="text-lg font-bold text-gray-900 mb-4 px-1">📅 과목별 일괄 연기</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-10">
                {subjects.map(subject => {
                    const style = getSubjectStyle(subject);
                    const processingTarget = `push-${subject}`;
                    const loading = isProcessing === processingTarget;

                    return (
                        <div key={`push-${subject}`} className={`bg-white rounded-xl p-4 border border-gray-100 shadow-sm flex flex-col items-center justify-center text-center transition-all hover:border-${style.accent} hover:shadow-md`}>
                            <div className="text-3xl mb-2">{style.icon}</div>
                            <div className={`font-bold text-base mb-1 ${style.accent}`}>{subject}</div>
                            <div className="text-xs text-gray-400 font-medium mb-4">일정 미루기</div>
                            <button
                                className={`w-full py-2 px-3 text-xs font-bold rounded-lg transition-colors border field-sizing-content
                  ${loading ? 'bg-gray-100 text-gray-400 border-gray-100' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50 hover:border-gray-300 shadow-sm'}`}
                                onClick={() => pushSchedule(subject, pushDays, pushFrom)}
                                disabled={loading}
                            >
                                {loading ? "..." : `+${pushDays}일 연기`}
                            </button>
                        </div>
                    );
                })}
            </div>

            <h3 className="text-lg font-bold text-gray-900 mb-4 px-1">➕ 수업 연장 (최근 1시간 차시 복제)</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 pb-12">
                {subjects.map(subject => {
                    const style = getSubjectStyle(subject);
                    const processingTarget = `ext-${subject}`;
                    const loading = isProcessing === processingTarget;

                    return (
                        <div key={`ext-${subject}`} className="bg-gray-50 rounded-xl p-4 border border-dashed border-gray-200 flex flex-col items-center justify-center text-center transition-colors hover:bg-white hover:border-solid hover:border-gray-300">
                            <div className="font-bold text-gray-800 text-base mb-1">{subject} 연장</div>
                            <div className="text-xs text-gray-500 font-medium mb-4">미완료 차시 유지<br />날짜만 밀기</div>
                            <button
                                className={`w-full py-2 px-3 text-xs font-bold rounded-lg text-white shadow-sm transition-transform 
                  ${loading ? 'bg-gray-300 transform-none' : 'hover:-translate-y-0.5'}`}
                                style={!loading ? { backgroundColor: 'currentColor' } : undefined}
                                onClick={() => extendSchedule(subject)}
                                disabled={loading}
                            >
                                {loading ? "처리중..." : "연장하기"}
                            </button>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
