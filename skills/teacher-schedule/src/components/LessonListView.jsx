import { getSubjectStyle } from "../lib/constants";

const PDF_BASE = "http://127.0.0.1:5000/api/pdf";
const SECTION_ORDER = ["today", "tomorrow", "nextweek"];
const SECTION_LABELS = {
    today: "오늘 배치",
    tomorrow: "내일 배치",
    nextweek: "다음 주 배치",
};

function getRecordKey(item) {
    return item?.lesson_id || item?._record_key || item?._row || "";
}

function getActionKey(item) {
    return item?._bridge_row || getRecordKey(item);
}

function getTitle(item) {
    return item?.["수업내용"] || item?.title || "제목 없음";
}

function getSubject(item) {
    return item?.["과목"] || item?.subject || "";
}

function getLesson(item) {
    return item?.["차시"] || item?.lesson || "";
}

function getUnit(item) {
    return item?.["대단원"] || item?.unit || "";
}

function getDate(item) {
    return item?.["계획일"] || item?.slot_date || "";
}

function getPeriod(item) {
    return item?.["계획교시"] || item?.slot_period || "";
}

function getPdfPath(item) {
    return item?.["pdf파일"] || item?.pdf_file || "";
}

function formatPlacement(item) {
    const plannedDate = getDate(item);
    const plannedPeriod = getPeriod(item);
    if (plannedDate && plannedPeriod) {
        return `${plannedDate} · ${plannedPeriod}교시`;
    }
    if (plannedDate) {
        return plannedDate;
    }
    if (plannedPeriod) {
        return `${plannedPeriod}교시`;
    }
    return "배치 정보 없음";
}

function PlacementCard({ item, markDone, marking }) {
    const subject = getSubject(item);
    const style = getSubjectStyle(subject);
    const actionKey = getActionKey(item);
    const recordKey = getRecordKey(item);
    const isProcessing = marking === actionKey;

    return (
        <article className="rounded-[26px] border border-stone-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
            <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                    <div className={`flex h-12 w-12 items-center justify-center rounded-2xl text-xl ${style.bg} ${style.accent}`}>
                        {style.icon}
                    </div>
                    <div>
                        <div className={`text-sm font-black ${style.accent}`}>{subject}</div>
                        <div className="mt-1 text-xs font-semibold text-stone-400">
                            {formatPlacement(item)}
                        </div>
                    </div>
                </div>
                <div className="rounded-full bg-stone-100 px-3 py-1 text-xs font-bold text-stone-500">
                    {getLesson(item)}차시
                </div>
            </div>

            <div className="mt-4 text-base font-bold leading-snug text-stone-900">
                {getTitle(item)}
            </div>
            {getUnit(item) && <div className="mt-2 text-sm text-stone-500">{getUnit(item)}</div>}

            <div className="mt-4 flex flex-wrap gap-2">
                {getPdfPath(item) && (
                    <a
                        href={`${PDF_BASE}/${encodeURIComponent(recordKey)}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center justify-center rounded-2xl border border-stone-200 bg-stone-50 px-4 py-2 text-sm font-bold text-stone-700 transition hover:bg-stone-100"
                    >
                        PDF 보기
                    </a>
                )}
                <button
                    className={`inline-flex items-center justify-center rounded-2xl px-4 py-2 text-sm font-bold text-white transition ${
                        isProcessing ? "cursor-not-allowed bg-stone-300" : "bg-stone-900 hover:-translate-y-0.5"
                    }`}
                    onClick={() => markDone(item)}
                    disabled={isProcessing}
                >
                    {isProcessing ? "처리 중..." : "이 슬롯 완료"}
                </button>
            </div>
        </article>
    );
}

function PlacementSection({ view, markDone, marking }) {
    const items = Array.isArray(view?.data) ? view.data : [];

    return (
        <section className="rounded-[30px] border border-stone-200 bg-[#fffdfa] p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <div className="text-[11px] font-bold uppercase tracking-[0.24em] text-stone-400">
                        {view.id.toUpperCase()}
                    </div>
                    <h3 className="mt-1 text-xl font-black text-stone-900">
                        {SECTION_LABELS[view.id] || view.title || view.label}
                    </h3>
                </div>
                <div className="rounded-full border border-stone-200 bg-white px-3 py-1 text-sm font-bold text-stone-500">
                    {items.length}개
                </div>
            </div>

            {items.length === 0 ? (
                <div className="mt-5 rounded-3xl border border-dashed border-stone-200 bg-white px-4 py-12 text-center text-sm font-semibold text-stone-400">
                    배치된 수업이 없습니다.
                </div>
            ) : (
                <div className="mt-5 space-y-4">
                    {items.map((item, index) => (
                        <PlacementCard
                            key={`${getActionKey(item) || getRecordKey(item) || index}`}
                            item={item}
                            markDone={markDone}
                            marking={marking}
                        />
                    ))}
                </div>
            )}
        </section>
    );
}

export function LessonListView({ views, markDone, marking }) {
    const sections = SECTION_ORDER.map((id) => views.find((view) => view.id === id)).filter(Boolean);
    const totalScheduled = sections.reduce(
        (sum, section) => sum + (Array.isArray(section.data) ? section.data.length : 0),
        0,
    );

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <section className="rounded-[32px] border border-stone-200 bg-[linear-gradient(135deg,#fff7ed_0%,#fffbeb_45%,#ffffff_100%)] p-6 shadow-sm">
                <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
                    <div>
                        <div className="text-[11px] font-bold uppercase tracking-[0.28em] text-amber-600">
                            Placement Board
                        </div>
                        <h2 className="mt-3 text-3xl font-black tracking-tight text-stone-900">
                            실제 수업배치를 날짜와 교시 기준으로 봅니다.
                        </h2>
                        <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
                            여기서는 브릿지 시트의 슬롯을 기준으로 오늘, 내일, 다음 주 배치를 확인합니다.
                            완료 버튼도 개별 슬롯을 닫는 방식으로 동작합니다.
                        </p>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-3">
                        {sections.map((section) => (
                            <div key={section.id} className="rounded-[24px] border border-amber-200/60 bg-white/80 px-4 py-4 shadow-sm">
                                <div className="text-[11px] font-bold uppercase tracking-[0.22em] text-stone-400">
                                    {SECTION_LABELS[section.id] || section.id}
                                </div>
                                <div className="mt-2 text-3xl font-black text-stone-900">
                                    {Array.isArray(section.data) ? section.data.length : 0}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="mt-5 rounded-2xl border border-amber-100 bg-white/70 px-4 py-3 text-sm text-stone-600">
                    총 <span className="font-black text-stone-900">{totalScheduled}</span>개의 예정 슬롯이 보이고 있습니다.
                    진도 요약은 진도표 탭에서 확인할 수 있습니다.
                </div>
            </section>

            <div className="grid gap-6 xl:grid-cols-3">
                {sections.map((section) => (
                    <PlacementSection
                        key={section.id}
                        view={section}
                        markDone={markDone}
                        marking={marking}
                    />
                ))}
            </div>
        </div>
    );
}
