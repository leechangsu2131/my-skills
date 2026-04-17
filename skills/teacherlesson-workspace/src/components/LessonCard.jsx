"use client";

import { SUBJECTS } from "@/lib/demoData";

function subjectColor(name) {
    const s = SUBJECTS.find((s) => s.name === name);
    return s ? s.color : "#005bbf";
}

export function LessonCard({ slot, onMarkDone, onAdjustPacing, onOpenPdf, onCopyPdfPath, compact = false }) {
    const isDone = slot.status === "done";
    const color = subjectColor(slot.subject);

    return (
        <div className={`card ${compact ? "card-compact" : ""}`}>
            <div className={`lesson-card${isDone ? " done" : ""}`}>
                {/* Period Badge */}
                <div
                    className="lesson-card-period"
                    style={
                        isDone
                            ? { background: "var(--secondary-container)" }
                            : { background: `${color}12` }
                    }
                >
                    {slot.slot_period}
                    <small>교시</small>
                </div>

                {/* Body */}
                <div className="lesson-card-body">
                    <span className="lesson-card-subject" style={{ color }}>
                        {slot.subject}
                    </span>
                    <span className="lesson-card-title">
                        {slot.lesson_number}차시 — {slot.title}
                    </span>
                    {slot.unit && (
                        <span className="lesson-card-unit">{slot.unit}</span>
                    )}
                </div>

                {/* Actions */}
                <div className="lesson-card-actions">
                    {!compact && (
                        <>
                            <button
                                className="btn btn-tertiary btn-sm"
                                onClick={() => onAdjustPacing?.(slot.id, "extend")}
                                title="현재 수업 1차시 연장"
                            >
                                연장
                            </button>
                            <button
                                className="btn btn-tertiary btn-sm"
                                onClick={() => onAdjustPacing?.(slot.id, "pull_next")}
                                title="다음 차시 당겨오기"
                            >
                                당겨오기
                            </button>
                            <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => onOpenPdf?.(slot)}
                                title="PDF 열기"
                            >
                                PDF
                            </button>
                            <button
                                className="btn btn-tertiary btn-sm"
                                onClick={() => onCopyPdfPath?.(slot)}
                                title="PDF 주소 복사"
                            >
                                주소복사
                            </button>
                        </>
                    )}
                    {isDone ? (
                        <span
                            className="status-badge done"
                            style={{ cursor: "pointer" }}
                            onClick={() => onMarkDone?.(slot.id)}
                            title="완료 취소"
                        >
                            ✓ 완료
                        </span>
                    ) : (
                        <button
                            className="btn btn-done btn-sm"
                            onClick={() => onMarkDone?.(slot.id)}
                            title="완료 처리"
                        >
                            완료
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
