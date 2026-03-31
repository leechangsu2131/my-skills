import { getSubjectStyle } from "../lib/constants";

export function LessonListView({ views, markDone, marking }) {
    const lessonViews = views.filter(v => v.type === "lesson_list");

    let allData = [];
    lessonViews.forEach(v => {
        if (v.data && v.data.length > 0) {
            allData = allData.concat(v.data);
        }
    });

    // Remove duplicates by _row
    const uniqueData = Array.from(new Map(allData.map(item => [item._row || item.행번호, item])).values());

    if (uniqueData.length === 0) {
        return (
            <div className="text-center py-16 px-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="text-6xl mb-4">🎉</div>
                <p className="text-lg text-gray-500 font-medium">조회된 미완료 수업이 없습니다.</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {uniqueData.map((item, i) => {
                const style = getSubjectStyle(item.과목);
                const rowId = item._row || item.행번호;
                const isProcessing = marking === rowId;

                return (
                    <div key={i} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 flex items-center gap-5 transition-shadow hover:shadow-md">
                        <div className={`w-14 h-14 rounded-xl flex items-center justify-center text-2xl flex-shrink-0 ${style.bg} ${style.accent}`}>
                            {style.icon}
                        </div>

                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                                <span className={`text-xs font-bold px-2.5 py-0.5 rounded-md ${style.bg} ${style.accent}`}>
                                    {item.과목}
                                </span>
                                <span className="text-xs font-bold text-gray-600 bg-gray-100 px-2 py-0.5 rounded-md">{item.차시}차시</span>
                                {item.계획일 && <span className="text-xs text-gray-400 font-medium">({item.계획일})</span>}
                            </div>

                            <h4 className="text-base font-bold text-gray-900 truncate mb-0.5">{item.수업내용}</h4>
                            <p className="text-sm font-medium text-gray-500">{item.대단원}</p>
                        </div>

                        <button
                            className={`flex-shrink-0 px-5 py-2.5 rounded-xl font-bold text-sm text-white shadow-sm transition-all focus:ring-4 focus:ring-opacity-50
                ${isProcessing ? "bg-gray-300 transform-none cursor-not-allowed" : "hover:-translate-y-0.5"}`}
                            style={!isProcessing ? { backgroundColor: 'currentColor' } : undefined}
                            onClick={() => markDone(item)}
                            disabled={isProcessing}
                        >
                            {isProcessing ? "처리중..." : "수업 완료 ✓"}
                        </button>
                    </div>
                );
            })}
        </div>
    );
}
