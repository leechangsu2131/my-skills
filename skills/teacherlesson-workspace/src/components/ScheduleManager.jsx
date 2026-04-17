"use client";

import { useState } from "react";

export function ScheduleManager({
    slots,
    subjects,
    selectedSubject,
    onSelectSubject,
    showToast,
}) {
    const [pushDays, setPushDays] = useState(7);
    const [pushSubject, setPushSubject] = useState(
        selectedSubject || subjects[0]?.name || ""
    );

    const handlePush = () => {
        showToast(
            `${pushSubject} 과목 수업을 ${pushDays}일 뒤로 이동했습니다. (데모)`
        );
    };

    const handleExtend = () => {
        showToast(`${pushSubject} 다음 수업을 1차시 연장했습니다. (데모)`);
    };

    const handlePull = () => {
        showToast(`${pushSubject} 다음 차시를 당겨왔습니다. (데모)`);
    };

    return (
        <div>
            {/* Push Schedule */}
            <div className="action-group">
                <h3 className="action-group-title">📅 과목 전체 뒤로 밀기</h3>
                <p
                    className="body-md text-variant"
                    style={{ marginBottom: "var(--sp-4)" }}
                >
                    특정 과목의 예정 수업을 일괄적으로 뒤로 이동합니다.
                </p>

                <div className="action-row">
                    <select
                        className="input-filled"
                        style={{ maxWidth: 180 }}
                        value={pushSubject}
                        onChange={(e) => setPushSubject(e.target.value)}
                    >
                        {subjects.map((s) => (
                            <option key={s.id} value={s.name}>
                                {s.name}
                            </option>
                        ))}
                    </select>

                    <input
                        type="number"
                        className="input-filled"
                        style={{ maxWidth: 100 }}
                        value={pushDays}
                        onChange={(e) => setPushDays(Number(e.target.value))}
                        min={1}
                        max={60}
                    />
                    <span className="label-md text-variant">일</span>

                    <button className="btn btn-primary" onClick={handlePush}>
                        밀기
                    </button>
                </div>
            </div>

            {/* Extend Lesson */}
            <div className="action-group">
                <h3 className="action-group-title">➕ 이 수업 한 차시 더</h3>
                <p
                    className="body-md text-variant"
                    style={{ marginBottom: "var(--sp-4)" }}
                >
                    현재 수업이 다음 같은 과목 시간까지 이어지도록 1차시를 더 확보합니다.
                </p>

                <div className="action-row">
                    <select
                        className="input-filled"
                        style={{ maxWidth: 180 }}
                        value={pushSubject}
                        onChange={(e) => setPushSubject(e.target.value)}
                    >
                        {subjects.map((s) => (
                            <option key={s.id} value={s.name}>
                                {s.name}
                            </option>
                        ))}
                    </select>

                    <button className="btn btn-secondary" onClick={handleExtend}>
                        연장
                    </button>
                </div>
            </div>

            {/* Pull Next Lesson */}
            <div className="action-group">
                <h3 className="action-group-title">⬆️ 다음 차시 당겨오기</h3>
                <p
                    className="body-md text-variant"
                    style={{ marginBottom: "var(--sp-4)" }}
                >
                    현재 슬롯 자리에 같은 과목의 다음 수업을 당겨옵니다.
                </p>

                <div className="action-row">
                    <select
                        className="input-filled"
                        style={{ maxWidth: 180 }}
                        value={pushSubject}
                        onChange={(e) => setPushSubject(e.target.value)}
                    >
                        {subjects.map((s) => (
                            <option key={s.id} value={s.name}>
                                {s.name}
                            </option>
                        ))}
                    </select>

                    <button className="btn btn-secondary" onClick={handlePull}>
                        당기기
                    </button>
                </div>
            </div>

            {/* Swap (placeholder) */}
            <div className="action-group">
                <h3 className="action-group-title">🔄 교환</h3>
                <p
                    className="body-md text-variant"
                    style={{ marginBottom: "var(--sp-4)" }}
                >
                    두 슬롯의 날짜/교시를 바꿉니다.
                </p>

                <div className="action-row">
                    <span className="label-md text-variant">
                        이 탭의 교환 기능은 아직 데모 상태입니다.
                    </span>
                </div>
            </div>

            {/* Info Panel */}
            <div
                className="card"
                style={{
                    marginTop: "var(--sp-6)",
                    background: "var(--secondary-container)",
                }}
            >
                <div style={{ display: "flex", gap: "var(--sp-3)", alignItems: "flex-start" }}>
                    <span style={{ fontSize: "1.5rem" }}>💡</span>
                    <div>
                        <p className="title-md" style={{ marginBottom: "var(--sp-2)" }}>
                            현재 동작 상태
                        </p>
                        <p className="body-md text-variant">
                            수업 배치/진도 화면의 완료, 연장, 당겨오기는 Supabase에 실제 저장됩니다.
                            이 일정 관리 탭의 일부 버튼은 아직 데모 메시지로만 동작합니다.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
