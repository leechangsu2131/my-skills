"use client";

import { useMemo } from "react";
import { SUBJECTS, formatDateKR, groupByDate } from "@/lib/demoData";

function subjectColor(name) {
    const s = SUBJECTS.find((s) => s.name === name);
    return s ? s.color : "#005bbf";
}

export function WeeklyBoard({ slots, week, today, onWeekChange, onMarkDone }) {
    const byDate = useMemo(() => groupByDate(slots), [slots]);
    const dayNames = ["월", "화", "수", "목", "금"];

    return (
        <div>
            {/* Week Navigation */}
            <div className="week-nav">
                <button
                    className="btn-icon"
                    onClick={() => onWeekChange(-1)}
                    title="이전 주"
                >
                    ◀
                </button>
                <span className="week-nav-label">
                    {formatDateKR(week.start)} ~ {formatDateKR(week.end)}
                </span>
                <button
                    className="btn-icon"
                    onClick={() => onWeekChange(1)}
                    title="다음 주"
                >
                    ▶
                </button>
                <button
                    className="btn btn-tertiary btn-sm"
                    onClick={() => onWeekChange(0)}
                    style={{ marginLeft: "var(--sp-2)" }}
                >
                    이번 주
                </button>
            </div>

            {/* Board Grid */}
            <div className="weekly-board">
                {week.days.map((dateStr, i) => {
                    const daySlots = byDate[dateStr] || [];
                    const isToday = dateStr === today;

                    return (
                        <div className="day-column" key={dateStr}>
                            {/* Day Header */}
                            <div className={`day-column-header${isToday ? " today" : ""}`}>
                                <div className="day-column-header-name">{dayNames[i]}</div>
                                <div className="day-column-header-date">
                                    {new Date(dateStr + "T00:00:00").getDate()}
                                </div>
                            </div>

                            {/* Slots */}
                            {daySlots.length === 0 ? (
                                <div
                                    style={{
                                        padding: "var(--sp-4)",
                                        textAlign: "center",
                                        color: "var(--on-surface-variant)",
                                        opacity: 0.4,
                                        fontSize: "var(--fs-label-sm)",
                                    }}
                                >
                                    수업 없음
                                </div>
                            ) : (
                                daySlots.map((slot) => (
                                    <div
                                        key={slot.id}
                                        className={`day-slot${slot.status === "done" ? " done" : ""}`}
                                        onClick={() => onMarkDone?.(slot.id)}
                                        title={`${slot.lesson_number}차시 — ${slot.title}\n클릭으로 완료 토글`}
                                    >
                                        <div className="day-slot-period">
                                            {slot.slot_period}교시
                                        </div>
                                        <div
                                            className="day-slot-subject"
                                            style={{ color: subjectColor(slot.subject) }}
                                        >
                                            {slot.subject}
                                        </div>
                                        <div className="day-slot-title">{slot.title}</div>
                                        {slot.status === "done" && (
                                            <span
                                                className="status-badge done"
                                                style={{
                                                    marginTop: "var(--sp-2)",
                                                    fontSize: "0.625rem",
                                                }}
                                            >
                                                ✓ 완료
                                            </span>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
