"use client";

import { LessonCard } from "./LessonCard";

export function TimelineView({ timeline, onMarkDone }) {
    if (!timeline || timeline.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-state-icon">📊</div>
                <p className="empty-state-title">데이터가 없습니다</p>
                <p className="body-md text-variant">
                    과목별 수업 데이터가 아직 없습니다.
                </p>
            </div>
        );
    }

    return (
        <div>
            {/* Global Progress */}
            <div className="overview-grid" style={{ marginBottom: "var(--sp-10)" }}>
                {timeline.map((t) => (
                    <div key={t.subject} className="overview-card">
                        <div
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "var(--sp-2)",
                                marginBottom: "var(--sp-3)",
                            }}
                        >
                            <div
                                style={{
                                    width: 10,
                                    height: 10,
                                    borderRadius: "50%",
                                    background: t.color,
                                    flexShrink: 0,
                                }}
                            />
                            <span className="label-lg">{t.subject}</span>
                        </div>

                        <div
                            style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "baseline",
                                marginBottom: "var(--sp-2)",
                            }}
                        >
                            <span className="display-sm" style={{ fontFamily: "var(--font-display)" }}>
                                {t.done}
                            </span>
                            <span className="label-sm text-variant">/ {t.total}</span>
                        </div>

                        <div className="progress-bar-track">
                            <div
                                className="progress-bar-fill"
                                style={{ width: `${t.progress}%` }}
                            />
                        </div>
                    </div>
                ))}
            </div>

            {/* Per-Subject Detail */}
            {timeline.map((t) => (
                <div key={t.subject} className="timeline-subject">
                    <div className="timeline-subject-header">
                        <div
                            className="timeline-subject-dot"
                            style={{ background: t.color }}
                        />
                        <span className="timeline-subject-name">{t.subject}</span>
                        <span className="timeline-subject-stats">
                            {t.done}/{t.total} 완료 · {t.progress}%
                        </span>
                    </div>

                    <div className="timeline-items">
                        {t.items.map((slot) => (
                            <LessonCard
                                key={slot.id}
                                slot={slot}
                                onMarkDone={onMarkDone}
                                compact
                            />
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}
