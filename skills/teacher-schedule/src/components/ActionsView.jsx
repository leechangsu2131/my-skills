import { useState } from "react";
import { getSubjectStyle } from "../lib/constants";

export function ActionsView({ subjects, pushSchedule, extendSchedule, isProcessing }) {
    const [pushDays, setPushDays] = useState(7);
    const [pushFrom, setPushFrom] = useState("");

    const dayOptions = [1, 2, 3, 5, 7, 14];

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <section className="rounded-[32px] border border-stone-200 bg-[linear-gradient(135deg,#eff6ff_0%,#f8fafc_45%,#ffffff_100%)] p-6 shadow-sm">
                <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
                    <div>
                        <div className="text-[11px] font-bold uppercase tracking-[0.28em] text-sky-600">
                            Schedule Control
                        </div>
                        <h2 className="mt-3 text-3xl font-black tracking-tight text-stone-900">
                            수업배치 운영 도구
                        </h2>
                        <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
                            여기서 미루기와 차시 확장을 수행하면 진도표 표시 열도 함께 맞춰집니다.
                            즉, 수업배치를 실제 일정의 기준으로 다루는 화면입니다.
                        </p>
                    </div>

                    <div className="rounded-[28px] border border-sky-100 bg-white/80 p-5 shadow-sm">
                        <div className="text-sm font-bold text-stone-800">미루기 기본 설정</div>
                        <div className="mt-4 flex flex-wrap gap-2">
                            {dayOptions.map((days) => {
                                const active = pushDays === days;
                                return (
                                    <button
                                        key={days}
                                        className={`rounded-2xl px-4 py-2 text-sm font-bold transition ${
                                            active
                                                ? "bg-stone-900 text-white shadow-sm"
                                                : "border border-stone-200 bg-white text-stone-600 hover:bg-stone-50"
                                        }`}
                                        onClick={() => setPushDays(days)}
                                    >
                                        {days}일
                                    </button>
                                );
                            })}
                        </div>

                        <label className="mt-5 block text-sm font-bold text-stone-700">
                            기준 날짜
                        </label>
                        <p className="mt-1 text-xs text-stone-500">
                            비워 두면 해당 과목의 남은 모든 슬롯을 함께 미룹니다.
                        </p>
                        <input
                            type="date"
                            className="mt-3 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm font-medium text-stone-900 outline-none transition focus:border-stone-900 focus:bg-white"
                            value={pushFrom}
                            onChange={(event) => setPushFrom(event.target.value)}
                        />
                    </div>
                </div>
            </section>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {subjects.map((subject) => {
                    const style = getSubjectStyle(subject);
                    const pushing = isProcessing === `push-${subject}`;
                    const extending = isProcessing === `ext-${subject}`;

                    return (
                        <article
                            key={subject}
                            className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                        >
                            <div className="flex items-center gap-3">
                                <div className={`flex h-12 w-12 items-center justify-center rounded-2xl text-xl ${style.bg} ${style.accent}`}>
                                    {style.icon}
                                </div>
                                <div>
                                    <div className={`text-lg font-black ${style.accent}`}>{subject}</div>
                                    <div className="text-sm text-stone-500">수업배치 조정</div>
                                </div>
                            </div>

                            <div className="mt-5 grid gap-3">
                                <button
                                    className={`inline-flex items-center justify-between rounded-2xl px-4 py-3 text-sm font-bold transition ${
                                        pushing
                                            ? "cursor-not-allowed bg-stone-200 text-stone-400"
                                            : "bg-stone-900 text-white hover:-translate-y-0.5"
                                    }`}
                                    onClick={() => pushSchedule(subject, pushDays, pushFrom || null)}
                                    disabled={pushing}
                                >
                                    <span>{pushDays}일 미루기</span>
                                    <span>{pushing ? "..." : "push"}</span>
                                </button>

                                <button
                                    className={`inline-flex items-center justify-between rounded-2xl border px-4 py-3 text-sm font-bold transition ${
                                        extending
                                            ? "cursor-not-allowed border-stone-200 bg-stone-100 text-stone-400"
                                            : "border-stone-200 bg-stone-50 text-stone-700 hover:-translate-y-0.5 hover:bg-white"
                                    }`}
                                    onClick={() => extendSchedule(subject)}
                                    disabled={extending}
                                >
                                    <span>1차시 확장</span>
                                    <span>{extending ? "..." : "extend"}</span>
                                </button>
                            </div>

                            <div className="mt-4 rounded-2xl bg-stone-50 px-4 py-3 text-xs leading-5 text-stone-500">
                                미루기는 날짜를 뒤로 보내고, 확장은 현재 진행 중인 차시 뒤에 같은 수업 슬롯을 하나 더 만듭니다.
                            </div>
                        </article>
                    );
                })}
            </div>
        </div>
    );
}
