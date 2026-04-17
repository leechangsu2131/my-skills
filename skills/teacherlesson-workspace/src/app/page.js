"use client";

import { useState, useMemo, useCallback } from "react"; // eslint-disable-line
import { WeeklyBoard } from "@/components/WeeklyBoard";
import { MonthlyCalendar } from "@/components/MonthlyCalendar";
import { TimelineView } from "@/components/TimelineView";
import { ScheduleManager } from "@/components/ScheduleManager";
import { LessonCard } from "@/components/LessonCard";
import { useSupabaseData } from "@/hooks/useSupabaseData";
import {
  buildSubjectTimeline,
  todayStr,
  formatDateKR,
  getWeekRange,
} from "@/lib/demoData";

function toLocalDateStr(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const TAB_CONFIG = {
  placements: {
    label: "수업 배치",
    eyebrow: "Placement Board",
    title: "오늘, 다음 수업일, 주간·월간 배치를 함께 봅니다.",
    icon: "📋",
  },
  progress: {
    label: "진도 현황",
    eyebrow: "Timeline Board",
    title: "과목별로 어떤 수업이 언제 있는지 흐름으로 봅니다.",
    icon: "📊",
  },
  actions: {
    label: "일정 관리",
    eyebrow: "Schedule Control",
    title: "과목 전체 이동, 개별 수업 조정을 처리합니다.",
    icon: "⚙️",
  },
};

export default function Home() {
  const [activeTab, setActiveTab] = useState("placements");
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [toast, setToast] = useState(null);
  const [boardDate, setBoardDate] = useState(todayStr());

  const today = todayStr();
  const week = useMemo(() => getWeekRange(boardDate), [boardDate]);

  const {
    slots,
    allSlots,
    weekSlots,
    todaySlots,
    subjects: dbSubjects,
    loading,
    usingDemo,
    markDone: handleMarkDone,
    adjustPacing: handleAdjustPacing,
    copyPdfPath,
    openPdf,
  } = useSupabaseData({ boardDate, selectedSubject });

  const filteredSlots = slots;

  const timeline = useMemo(
    () => buildSubjectTimeline(filteredSlots),
    [filteredSlots]
  );

  const subjectCounts = useMemo(() => {
    const counts = {};
    for (const s of allSlots) {
      counts[s.subject] = (counts[s.subject] || 0) + 1;
    }
    return counts;
  }, [allSlots]);

  const totalDone = useMemo(
    () => allSlots.filter((s) => s.status === "done").length,
    [allSlots]
  );

  const showToast = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  }, []);

  const handlePacing = useCallback(async (slotId, pacing) => {
    const ok = await handleAdjustPacing(slotId, pacing);
    if (!ok) {
      showToast("진도 조정에 실패했습니다.");
      return;
    }
    showToast(pacing === "extend" ? "현재 수업을 1차시 연장했습니다." : "다음 차시를 이번 교시에 당겨왔습니다.");
  }, [handleAdjustPacing, showToast]);

  const handleOpenPdf = useCallback((slot) => {
    const ok = openPdf(slot);
    showToast(ok ? "PDF를 새 탭에서 열었습니다." : "열 수 있는 PDF 주소가 없습니다.");
  }, [openPdf, showToast]);

  const handleCopyPdfPath = useCallback(async (slot) => {
    const ok = await copyPdfPath(slot);
    showToast(ok ? "PDF 주소를 복사했습니다." : "복사할 PDF 주소가 없습니다.");
  }, [copyPdfPath, showToast]);

  const handleWeekChange = useCallback(
    (dir) => {
      if (dir === 0) {
        setBoardDate(todayStr());
        return;
      }
      const d = new Date(boardDate + "T00:00:00");
      d.setDate(d.getDate() + dir * 7);
      setBoardDate(toLocalDateStr(d));
    },
    [boardDate]
  );

  const tab = TAB_CONFIG[activeTab];

  const activeSubjects = dbSubjects.filter((s) => subjectCounts[s.name]);

  return (
    <div className="app-shell">
      {/* ---- Sidebar ---- */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>Teacher Workspace</h1>
          <p>통합 수업 관리</p>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-section-label">Views</div>
          {Object.entries(TAB_CONFIG).map(([key, cfg]) => (
            <button
              key={key}
              className={`tab-btn${activeTab === key ? " active" : ""}`}
              onClick={() => setActiveTab(key)}
            >
              <span className="tab-btn-icon">{cfg.icon}</span>
              {cfg.label}
            </button>
          ))}
        </nav>

        {/* Subject Filter */}
        <div>
          <div className="sidebar-section-label">과목 필터</div>
          <div className="sidebar-nav">
            <button
              className={`tab-btn${selectedSubject === null ? " active" : ""}`}
              onClick={() => setSelectedSubject(null)}
            >
              <span className="tab-btn-icon">🔵</span>
              전체
              <span className="tab-btn-meta">{slots.length}</span>
            </button>
            {activeSubjects.map((s) => (
              <button
                key={s.id}
                className={`tab-btn${selectedSubject === s.name ? " active" : ""}`}
                onClick={() => setSelectedSubject(s.name === selectedSubject ? null : s.name)}
              >
                <span
                  className="tab-btn-icon"
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    background: s.color,
                  }}
                />
                {s.name}
                <span className="tab-btn-meta">
                  {subjectCounts[s.name] || 0}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Bottom stats */}
        <div style={{ marginTop: "auto", padding: "0 var(--sp-3)" }}>
          <p className="label-sm text-variant">
            이번 주 {totalDone}/{slots.length}개 완료
          </p>
          <div className="progress-bar-track" style={{ marginTop: "var(--sp-2)" }}>
            <div
              className="progress-bar-fill"
              style={{
                width: `${slots.length > 0 ? (totalDone / slots.length) * 100 : 0}%`,
              }}
            />
          </div>
        </div>
      </aside>

      {/* ---- Main Content ---- */}
      <main className="main-content">
        <header className="page-header">
          <p className="page-eyebrow">{tab.eyebrow}</p>
          <h2 className="page-title">{tab.label}</h2>
          <p className="page-subtitle">{tab.title}</p>
        </header>

        {/* Tab content */}
        {activeTab === "placements" && (
          <>
            {/* Overview Cards */}
            <div className="overview-grid">
              <div className="overview-card">
                <p className="overview-card-label">오늘의 수업</p>
                <p className="overview-card-value">{todaySlots.length}</p>
                <p className="overview-card-desc">{formatDateKR(today)}</p>
              </div>
              <div className="overview-card">
                <p className="overview-card-label">이번 주</p>
                <p className="overview-card-value">{weekSlots.length}</p>
                <p className="overview-card-desc">
                  {formatDateKR(week.start)} ~ {formatDateKR(week.end)}
                </p>
              </div>
              <div className="overview-card">
                <p className="overview-card-label">완료됨</p>
                <p className="overview-card-value">{totalDone}</p>
                <p className="overview-card-desc">전체 {slots.length}개 중</p>
              </div>
              <div className="overview-card">
                <p className="overview-card-label">과목 수</p>
                <p className="overview-card-value">
                  {activeSubjects.length}
                </p>
                <p className="overview-card-desc">활성 과목</p>
              </div>
            </div>

            {/* Today's Lessons */}
            {todaySlots.length > 0 && (
              <section className="section">
                <div className="section-header">
                  <h3 className="section-title">
                    오늘의 수업
                    <span className="section-count">
                      {todaySlots.length}
                    </span>
                  </h3>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-2)" }}>
                  {todaySlots.map((slot) => (
                    <LessonCard
                      key={slot.id}
                      slot={slot}
                      onMarkDone={handleMarkDone}
                      onAdjustPacing={handlePacing}
                      onOpenPdf={handleOpenPdf}
                      onCopyPdfPath={handleCopyPdfPath}
                    />
                  ))}
                </div>
              </section>
            )}

            {/* Weekly Board */}
            <section className="section">
              <WeeklyBoard
                slots={weekSlots}
                week={week}
                today={today}
                onWeekChange={handleWeekChange}
                onMarkDone={handleMarkDone}
                onAdjustPacing={handlePacing}
                onOpenPdf={handleOpenPdf}
                onCopyPdfPath={handleCopyPdfPath}
              />
            </section>

            {/* Monthly Calendar */}
            <section className="section">
              <MonthlyCalendar slots={slots} boardDate={boardDate} />
            </section>
          </>
        )}

        {activeTab === "progress" && (
          <TimelineView
            timeline={timeline}
            onMarkDone={handleMarkDone}
            onOpenPdf={handleOpenPdf}
            onCopyPdfPath={handleCopyPdfPath}
          />
        )}

        {activeTab === "actions" && (
          <ScheduleManager
            slots={slots}
            subjects={activeSubjects}
            selectedSubject={selectedSubject}
            onSelectSubject={setSelectedSubject}
            showToast={showToast}
          />
        )}
      </main>

      {/* Toast */}
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
