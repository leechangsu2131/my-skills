import { useEffect, useMemo, useState } from "react";
import { getSubjectStyle, subjectMatches } from "../lib/constants";
import {
    filterItemsBySubject,
    formatPlacement,
    getActionKey,
    getBridgeRow,
    getSubject,
    getTitle,
    isDoneItem,
} from "../lib/lessonFields";

function agendaLabel(item) {
    return `${formatPlacement(item)} · ${getSubject(item)} · ${getTitle(item)}`;
}

function AgendaCard({ item, pullLessonForward, extendSchedule, isProcessing }) {
    const subject = getSubject(item);
    const style = getSubjectStyle(subject);
    const bridgeRow = getBridgeRow(item);
    const rowNumber = item.row_number ?? item._row ?? null;
    const pullKey = `pull-${bridgeRow}`;
    const extendKey = `extend-${subject}-${bridgeRow || rowNumber || "next"}`;

    return (
        <article className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-3">
                <div className={`flex h-11 w-11 items-center justify-center rounded-2xl text-lg ${style.bg} ${style.accent}`}>
                    {style.icon}
                </div>
                <div className="min-w-0 flex-1">
                    <div className={`truncate text-sm font-black ${style.accent}`}>{subject}</div>
                    <div className="mt-1 truncate text-sm font-semibold text-slate-900">{getTitle(item)}</div>
                    <div className="mt-1 text-xs text-slate-500">{formatPlacement(item)}</div>
                </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
                <button
                    className={`inline-flex items-center justify-center rounded-2xl border px-4 py-2 text-sm font-bold transition ${
                        isProcessing === pullKey
                            ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
                            : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-white"
                    }`}
                    onClick={() => pullLessonForward(item)}
                    disabled={isProcessing === pullKey}
                    type="button"
                >
                    {isProcessing === pullKey ? "조정 중..." : "다음 차시 당겨오기"}
                </button>
                {!isDoneItem(item) && (
                    <button
                        className={`inline-flex items-center justify-center rounded-2xl border px-4 py-2 text-sm font-bold transition ${
                            isProcessing === extendKey
                                ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
                                : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-white"
                        }`}
                        onClick={() => extendSchedule(subject, rowNumber, bridgeRow)}
                        disabled={isProcessing === extendKey}
                        type="button"
                    >
                        {isProcessing === extendKey ? "연장 중..." : "이 수업 한 차시 더"}
                    </button>
                )}
            </div>
        </article>
    );
}

export function ActionsView({
    subjects,
    agendaItems,
    pushSchedule,
    extendSchedule,
    pullLessonForward,
    swapLessons,
    isProcessing,
    subjectFilter,
}) {
    const [pushDays, setPushDays] = useState(7);
    const [pushFrom, setPushFrom] = useState("");
    const [firstSwap, setFirstSwap] = useState("");
    const [secondSwap, setSecondSwap] = useState("");

    const dayOptions = [1, 2, 3, 5, 7, 14];
    const filteredSubjects = subjects.filter((subject) => subjectMatches(subject, subjectFilter));
    const filteredAgenda = filterItemsBySubject(agendaItems, subjectFilter).filter(
        (item) => getBridgeRow(item),
    );
    const swappableAgenda = filteredAgenda.filter(
        (item) => !isDoneItem(item),
    );

    useEffect(() => {
        if (firstSwap && !swappableAgenda.some((item) => String(getBridgeRow(item)) === String(firstSwap))) {
            setFirstSwap("");
        }
        if (secondSwap && !swappableAgenda.some((item) => String(getBridgeRow(item)) === String(secondSwap))) {
            setSecondSwap("");
        }
    }, [swappableAgenda, firstSwap, secondSwap]);

    const swapDisabled =
        !firstSwap ||
        !secondSwap ||
        firstSwap === secondSwap ||
        isProcessing === `swap-${firstSwap}-${secondSwap}`;

    const swapOptions = useMemo(
        () =>
            swappableAgenda.map((item) => ({
                value: String(getBridgeRow(item)),
                label: agendaLabel(item),
            })),
        [swappableAgenda],
    );

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <section className="rounded-[32px] border border-slate-200 bg-[linear-gradient(135deg,#eff6ff_0%,#f8fafc_45%,#ffffff_100%)] p-6 shadow-sm">
                <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
                    <div>
                        <div className="text-[11px] font-black uppercase tracking-[0.28em] text-sky-600">
                            Schedule Control
                        </div>
                        <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-900">
                            과목 단위로 밀고, 개별 수업 흐름은 당기거나 연장합니다.
                        </h2>
                        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                            개별 카드의 빠른 조정은 하루 안 교시 이동이 아니라, 같은 과목의 다음 수업 시간들 사이에서
                            진도를 당기거나 더 쓰는 방식으로 동작합니다.
                        </p>
                    </div>

                    <div className="rounded-[28px] border border-sky-100 bg-white/80 p-5 shadow-sm">
                        <div className="text-sm font-bold text-slate-800">과목 전체 이동 기본 설정</div>
                        <div className="mt-4 flex flex-wrap gap-2">
                            {dayOptions.map((days) => {
                                const active = pushDays === days;
                                return (
                                    <button
                                        key={days}
                                        className={`rounded-2xl px-4 py-2 text-sm font-bold transition ${
                                            active
                                                ? "bg-slate-950 text-white shadow-sm"
                                                : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                                        }`}
                                        onClick={() => setPushDays(days)}
                                        type="button"
                                    >
                                        {days}일
                                    </button>
                                );
                            })}
                        </div>

                        <label className="mt-5 block text-sm font-bold text-slate-700">기준 날짜</label>
                        <p className="mt-1 text-xs text-slate-500">
                            비워 두면 해당 과목의 모든 예정 수업을 같은 폭으로 뒤로 미룹니다.
                        </p>
                        <input
                            type="date"
                            className="mt-3 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-900 outline-none transition focus:border-slate-950 focus:bg-white"
                            value={pushFrom}
                            onChange={(event) => setPushFrom(event.target.value)}
                        />
                    </div>
                </div>
            </section>

            {filteredSubjects.length === 0 ? (
                <div className="rounded-[28px] border border-slate-200 bg-white p-8 text-center text-slate-500 shadow-sm">
                    선택한 과목이 없어 일정 관리 대상을 표시하지 못했습니다.
                </div>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {filteredSubjects.map((subject) => {
                        const style = getSubjectStyle(subject);
                        const pushing = isProcessing === `push-${subject}`;
                        const extending = isProcessing === `extend-${subject}-next`;

                        return (
                            <article
                                key={subject}
                                className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`flex h-12 w-12 items-center justify-center rounded-2xl text-xl ${style.bg} ${style.accent}`}>
                                        {style.icon}
                                    </div>
                                    <div>
                                        <div className={`text-lg font-black ${style.accent}`}>{subject}</div>
                                        <div className="text-sm text-slate-500">과목 단위 조정</div>
                                    </div>
                                </div>

                                <div className="mt-5 grid gap-3">
                                    <button
                                        className={`inline-flex items-center justify-between rounded-2xl px-4 py-3 text-sm font-bold transition ${
                                            pushing
                                                ? "cursor-not-allowed bg-slate-200 text-slate-400"
                                                : "bg-slate-950 text-white hover:-translate-y-0.5"
                                        }`}
                                        onClick={() => pushSchedule(subject, pushDays, pushFrom || null)}
                                        disabled={pushing}
                                        type="button"
                                    >
                                        <span>{pushDays}일 뒤로</span>
                                        <span>{pushing ? "..." : "push"}</span>
                                    </button>

                                    <button
                                        className={`inline-flex items-center justify-between rounded-2xl border px-4 py-3 text-sm font-bold transition ${
                                            extending
                                                ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
                                                : "border-slate-200 bg-slate-50 text-slate-700 hover:-translate-y-0.5 hover:bg-white"
                                        }`}
                                        onClick={() => extendSchedule(subject)}
                                        disabled={extending}
                                        type="button"
                                    >
                                        <span>현재 수업 한 차시 더</span>
                                        <span>{extending ? "..." : "extend"}</span>
                                    </button>
                                </div>

                                <div className="mt-4 rounded-2xl bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-500">
                                    과목 전체 이동은 앞으로 남은 수업 전체를 한꺼번에 미룰 때 쓰고, 개별 수업 조정은
                                    아래 예정 슬롯 카드에서 처리합니다.
                                </div>
                            </article>
                        );
                    })}
                </div>
            )}

            <section className="rounded-[30px] border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                    <div>
                        <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">SWAP LESSON SLOTS</div>
                        <h3 className="mt-1 text-2xl font-black text-slate-900">두 수업 시간 서로 바꾸기</h3>
                        <p className="mt-2 text-sm text-slate-500">
                            필요할 때는 개별 수업 두 개를 골라 날짜와 교시를 교환할 수 있습니다.
                        </p>
                    </div>
                    <button
                        className={`inline-flex items-center justify-center rounded-2xl px-5 py-3 text-sm font-bold text-white transition ${
                            swapDisabled
                                ? "cursor-not-allowed bg-slate-300"
                                : "bg-slate-950 hover:-translate-y-0.5"
                        }`}
                        onClick={() => swapLessons(firstSwap, secondSwap)}
                        disabled={swapDisabled}
                        type="button"
                    >
                        {swapDisabled && isProcessing?.startsWith("swap-") ? "교환 중..." : "선택한 두 수업 교환"}
                    </button>
                </div>
                <div className="mt-5 grid gap-4 lg:grid-cols-2">
                    <label className="block">
                        <div className="mb-2 text-sm font-bold text-slate-700">첫 번째 수업</div>
                        <select
                            className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none focus:border-slate-950 focus:bg-white"
                            value={firstSwap}
                            onChange={(event) => setFirstSwap(event.target.value)}
                        >
                            <option value="">수업을 선택하세요</option>
                            {swapOptions.map((option) => (
                                <option key={`first-${option.value}`} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className="block">
                        <div className="mb-2 text-sm font-bold text-slate-700">두 번째 수업</div>
                        <select
                            className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none focus:border-slate-950 focus:bg-white"
                            value={secondSwap}
                            onChange={(event) => setSecondSwap(event.target.value)}
                        >
                            <option value="">수업을 선택하세요</option>
                            {swapOptions.map((option) => (
                                <option key={`second-${option.value}`} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                    </label>
                </div>
            </section>

            <section className="space-y-4">
                <div className="flex items-end justify-between gap-4">
                    <div>
                        <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">AGENDA</div>
                        <h3 className="mt-1 text-2xl font-black text-slate-900">다가오는 예정 수업</h3>
                    </div>
                    <div className="text-sm font-semibold text-slate-500">{filteredAgenda.length}개 표시</div>
                </div>
                {filteredAgenda.length === 0 ? (
                    <div className="rounded-[28px] border border-slate-200 bg-white p-8 text-center text-slate-500 shadow-sm">
                        조정 가능한 예정 수업이 없습니다.
                    </div>
                ) : (
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                        {filteredAgenda.slice(0, 18).map((item) => (
                            <AgendaCard
                                key={getActionKey(item)}
                                item={item}
                                pullLessonForward={pullLessonForward}
                                extendSchedule={extendSchedule}
                                isProcessing={isProcessing}
                            />
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}
