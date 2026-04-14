import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://127.0.0.1:5000/api";

const SUBJECT_COLORS = {
  음악: { bg: "#FFF0E6", accent: "#E8724A", icon: "🎵" },
  사회: { bg: "#E6F0FF", accent: "#3B7DD8", icon: "🌍" },
  수학: { bg: "#E6FFF0", accent: "#2E9E5B", icon: "📐" },
  미술: { bg: "#F5E6FF", accent: "#9B4FCC", icon: "🎨" },
  국어: { bg: "#FFF5E6", accent: "#D87A3B", icon: "📖" },
  과학: { bg: "#E6FAFF", accent: "#1F9E89", icon: "🔬" },
  영어: { bg: "#F0E6FF", accent: "#8B5CF6", icon: "🔤" },
  체육: { bg: "#FFE6E6", accent: "#E53E3E", icon: "🏃" },
  실과: { bg: "#FFFFE6", accent: "#D69E2E", icon: "🔧" },
  도덕: { bg: "#E6FFE6", accent: "#A5A522", icon: "🤝" }
};

export default function App() {
  const [activeTab, setActiveTab] = useState("");
  const [views, setViews] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [marking, setMarking] = useState(null);
  const [pushSubject, setPushSubject] = useState(null);
  const [pushDays, setPushDays] = useState(7);
  const [pushFrom, setPushFrom] = useState("");
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/dashboard`);
      if (!res.ok) throw new Error("서버 응답 오류");
      const data = await res.json();
      setViews(data.views || []);
      setSubjects(data.subjects || []);
      setActiveTab(current => (data.views.find(v => v.id === current) ? current : "dashboard"));
    } catch (e) {
      showToast("데이터 로드 실패: " + e.message, "error");
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const markDone = async (item) => {
    const rowId = item._row || item.행번호;
    setMarking(rowId);
    try {
      const res = await fetch(`${API_BASE}/done`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject: item.과목, target_date: item.계획일 })
      });
      if (!res.ok) throw new Error("서버 에러");
      showToast(`✅ "${item.수업내용}" 완료 처리됨`);
      await loadData();
    } catch (e) {
      showToast("업데이트 실패: " + e.message, "error");
    }
    setMarking(null);
  };

  const pushSchedule = async (subj, days, fromDate = null) => {
    setPushSubject(subj);
    try {
      const res = await fetch(`${API_BASE}/push`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject: subj, days, from_date: fromDate || null })
      });
      if (!res.ok) throw new Error("서버 에러");
      showToast(`📅 ${subj} 연기 완료`);
      await loadData();
    } catch (e) {
      showToast("실패: " + e.message, "error");
    }
    setPushSubject(null);
  };

  const extendSchedule = async (subj) => {
    setPushSubject(subj);
    try {
      const res = await fetch(`${API_BASE}/extend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject: subj })
      });
      if (!res.ok) throw new Error("서버 에러");
      showToast(`⏳ ${subj} 연장 완료`);
      await loadData();
    } catch (e) {
      showToast("실패: " + e.message, "error");
    }
    setPushSubject(null);
  };

  // --- Components ---

  const OverallProgress = () => {
    const progView = views.find(v => v.id === "progress_list");
    if (!progView || !progView.data) return null;

    let totalClasses = 0;
    let totalDone = 0;
    Object.values(progView.data).forEach(p => {
      totalClasses += p.전체;
      totalDone += p.완료;
    });
    const percentage = totalClasses === 0 ? 0 : Math.round((totalDone / totalClasses) * 100);

    return (
      <div className="overall-progress-card glow-effect">
        <div className="flex-between" style={{ marginBottom: "16px" }}>
          <div>
            <h2 className="title-md" style={{ color: "#fff", opacity: 0.9 }}>전체 학기 진도율</h2>
            <p className="subtitle" style={{ color: "#a0aec0" }}>모든 과목 통합 기준</p>
          </div>
          <div className="percentage-display">
            {percentage}<span>%</span>
          </div>
        </div>
        <div className="progress-track-large">
          <div className="progress-fill-gradient" style={{ width: `${percentage}%` }}></div>
        </div>
        <div className="progress-stats">
          <span>총 {totalClasses}차시 중 {totalDone}차시 완료</span>
          <span>{totalClasses - totalDone}차시 남음</span>
        </div>
      </div>
    );
  };

  const DashboardView = () => {
    const nextView = views.find(v => v.id === "next_class_grid");
    const progView = views.find(v => v.id === "progress_list");

    if (!nextView || !progView) return <div className="empty-state">데이터가 없습니다.</div>;

    return (
      <div className="dashboard-grid fade-in">
        <OverallProgress />

        <h3 className="section-title" style={{ marginTop: "24px" }}>오늘 &amp; 다음 수업</h3>
        <div className="cards-grid">
          {Object.keys(nextView.data).map(sub => {
            const data = nextView.data[sub];
            const prog = progView.data[sub];
            const color = SUBJECT_COLORS[sub] || { bg: "#f7fafc", accent: "#4a5568", icon: "📚" };
            const nextCls = data?.next;

            if (!nextCls && prog?.완료 === prog?.전체) return null; // Fully completed subjects hidden from dashboard if you want, or just render them

            return (
              <div key={sub} className="subject-card interactive" style={{ borderTop: `4px solid ${color.accent}` }}>
                <div className="flex-between">
                  <div className="flex-center">
                    <span className="icon-large">{color.icon}</span>
                    <span className="subject-name" style={{ color: color.accent }}>{sub}</span>
                  </div>
                  <span className="prog-percent" style={{ background: color.bg, color: color.accent }}>
                    {prog ? prog.진도율 : "0%"}
                  </span>
                </div>

                {prog && (
                  <div className="progress-track-small mt-3">
                    <div className="progress-fill" style={{ width: prog.진도율, background: color.accent }}></div>
                  </div>
                )}

                {nextCls ? (
                  <div className="next-lesson-box mt-4">
                    <div className="next-badge">NOW</div>
                    <div className="lesson-title">{nextCls.수업내용}</div>
                    <div className="flex-between mt-2">
                      <span className="lesson-meta">{nextCls.차시}차시 • {nextCls.대단원}</span>
                      <button
                        className="btn-done-small"
                        style={{ background: color.accent }}
                        onClick={() => markDone(nextCls)}
                        disabled={marking === (nextCls._row || nextCls.행번호)}
                      >
                        {marking === (nextCls._row || nextCls.행번호) ? "..." : "완료 ✓"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="completed-box mt-4">
                    모든 진도 완료! 🎉
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const LessonListView = () => {
    const list = views.find(v => v.id === "lesson_list");
    if (!list || !list.data || list.data.length === 0) {
      return (
        <div className="empty-state mt-4 fade-in">
          <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🎉</div>
          선택한 기간(오늘/이번주 등)의 미완료 수업이 없습니다.
        </div>
      );
    }
    return (
      <div className="list-container fade-in">
        {list.data.map((item, i) => {
          const color = SUBJECT_COLORS[item.과목] || { bg: "#f7fafc", accent: "#4a5568", icon: "📚" };
          const rowId = item._row || item.행번호;
          return (
            <div key={i} className="list-item-card">
              <div className="icon-wrapper" style={{ background: color.bg, color: color.accent }}>
                {color.icon}
              </div>
              <div className="list-content">
                <div className="flex-center gap-2 mb-1">
                  <span className="badge" style={{ background: color.accent }}>{item.과목}</span>
                  <span className="meta-text">{item.차시}차시</span>
                  {item.계획일 && <span className="meta-date">({item.계획일})</span>}
                </div>
                <div className="item-title">{item.수업내용}</div>
                <div className="item-subtitle">{item.대단원}</div>
              </div>
              <button
                className="btn-done"
                style={{ background: marking === rowId ? "#cbd5e0" : color.accent }}
                onClick={() => markDone(item)}
                disabled={marking === rowId}
              >
                {marking === rowId ? "처리중..." : "수업 완료"}
              </button>
            </div>
          );
        })}
      </div>
    );
  };

  const ActionsView = () => {
    return (
      <div className="actions-container fade-in">
        <h3 className="section-title mb-3">⚙️ 일괄 연기 설정</h3>
        <div className="action-card mb-4" style={{ background: "#fff" }}>
          <label className="action-label">며칠을 미룰까요?</label>
          <div className="flex-wrap gap-2 mb-4">
            {[1, 2, 3, 5, 7, 14].map(d => (
              <button
                key={d}
                className={`btn-chip ${pushDays === d ? 'active' : ''}`}
                onClick={() => setPushDays(d)}
              >{d}일</button>
            ))}
          </div>
          <label className="action-label">언제부터 연기할까요? (비워두면 전체)</label>
          <input type="date" className="date-input" value={pushFrom} onChange={e => setPushFrom(e.target.value)} />
        </div>

        <h3 className="section-title mb-3">📅 일괄 연기</h3>
        <div className="cards-grid mb-6">
          {subjects.map(subject => {
            const color = SUBJECT_COLORS[subject] || { bg: "#f7fafc", accent: "#4a5568", icon: "📚" };
            return (
              <div key={subject} className="action-btn-card" style={{ borderColor: `${color.accent}33` }}>
                <div className="icon-large mb-2">{color.icon}</div>
                <div className="action-name" style={{ color: color.accent }}>{subject} 미루기</div>
                <button
                  className="btn-outline mt-3 w-full"
                  onClick={() => pushSchedule(subject, pushDays, pushFrom)}
                  disabled={pushSubject === subject}
                >
                  {pushSubject === subject ? "..." : `+${pushDays}일 연기`}
                </button>
              </div>
            );
          })}
        </div>

        <h3 className="section-title mb-3">➕ 수업 연장 (1시간 추가)</h3>
        <div className="cards-grid">
          {subjects.map(subject => {
            const color = SUBJECT_COLORS[subject] || { bg: "#f7fafc", accent: "#4a5568", icon: "📚" };
            return (
              <div key={`ext-${subject}`} className="action-btn-card dashed" style={{ borderColor: `${color.accent}66` }}>
                <div className="action-name" style={{ color: "#2d3748" }}>{subject} 연장</div>
                <div className="action-desc">최근 미완료 차시 복제</div>
                <button
                  className="btn-solid mt-3 w-full"
                  style={{ background: color.accent }}
                  onClick={() => extendSchedule(subject)}
                  disabled={pushSubject === subject}
                >
                  연장
                </button>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="app-container font-sans">
      <header className="app-header glass">
        <div className="header-inner">
          <div className="brand">
            <span className="brand-icon">📚</span>
            <div>
              <h1 className="brand-name">스마트 진도표</h1>
              <p className="brand-sub">Teacher Schedule Pro</p>
            </div>
          </div>
          <button className="btn-icon" onClick={loadData} disabled={loading} title="새로고침">
            {loading ? <span className="spinner">↻</span> : "⟳"}
          </button>
        </div>

        <div className="tabs-container">
          <button className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            대시보드
          </button>
          <button className={`tab-btn ${activeTab === 'lesson_list' ? 'active' : ''}`} onClick={() => setActiveTab('lesson_list')}>
            수업 목록
          </button>
          <button className={`tab-btn ${activeTab === 'actions' ? 'active' : ''}`} onClick={() => setActiveTab('actions')}>
            일정 관리
          </button>
        </div>
      </header>

      <main className="main-content">
        {loading && views.length === 0 ? (
          <div className="loader-full">
            <div className="spinner-large">⟳</div>
            <p>데이터 연동 중...</p>
          </div>
        ) : (
          <>
            {activeTab === 'dashboard' && <DashboardView />}
            {activeTab === 'lesson_list' && <LessonListView />}
            {activeTab === 'actions' && <ActionsView />}
          </>
        )}
      </main>

      {toast && (
        <div className={`toast-message toast-${toast.type}`}>
          {toast.msg}
        </div>
      )}

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap');
        
        :root {
          --bg-main: #f3f4f6;
          --bg-card: #ffffff;
          --text-main: #111827;
          --text-sub: #6b7280;
          --border: #e5e7eb;
          --primary: #4F46E5;
          --radius-md: 12px;
          --radius-lg: 20px;
          --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
          --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
          --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }

        body {
          margin: 0;
          background: var(--bg-main);
          color: var(--text-main);
          -webkit-font-smoothing: antialiased;
        }

        .font-sans {
          font-family: 'Pretendard', 'Inter', sans-serif;
        }

        .flex-between { display: flex; justify-content: space-between; align-items: center; }
        .flex-center { display: flex; align-items: center; }
        .gap-2 { gap: 0.5rem; }
        .mt-2 { margin-top: 0.5rem; }
        .mt-3 { margin-top: 0.75rem; }
        .mt-4 { margin-top: 1rem; }
        .mb-2 { margin-bottom: 0.5rem; }
        .mb-3 { margin-bottom: 0.75rem; }
        .mb-4 { margin-bottom: 1rem; }
        .mb-6 { margin-bottom: 1.5rem; }
        .w-full { width: 100%; }

        /* Animation */
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .fade-in { animation: fadeIn 0.4s ease forwards; }

        @keyframes spinner { to { transform: rotate(360deg); } }
        .spinner { display: inline-block; animation: spinner 1s linear infinite; }
        .spinner-large { display: inline-block; animation: spinner 1s linear infinite; font-size: 2.5rem; color: var(--primary); margin-bottom: 1rem; }

        .app-container {
          min-height: 100vh;
        }

        .app-header.glass {
          background: rgba(255, 255, 255, 0.85);
          backdrop-filter: blur(12px);
          position: sticky;
          top: 0;
          z-index: 50;
          border-bottom: 1px solid var(--border);
          padding-top: 1.5rem;
        }

        .header-inner {
          max-width: 800px;
          margin: 0 auto;
          padding: 0 1.5rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
        }

        .brand {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .brand-icon {
          font-size: 2rem;
        }

        .brand-name {
          margin: 0;
          font-size: 1.4rem;
          font-weight: 800;
          letter-spacing: -0.03em;
          color: #111827;
        }

        .brand-sub {
          margin: 0;
          font-size: 0.75rem;
          color: #6b7280;
          font-weight: 500;
        }

        .btn-icon {
          background: #f3f4f6;
          border: 1px solid #e5e7eb;
          width: 36px;
          height: 36px;
          border-radius: 10px;
          cursor: pointer;
          font-size: 1rem;
          color: #374151;
          transition: all 0.2s;
        }
        .btn-icon:hover:not(:disabled) {
          background: #e5e7eb;
        }

        .tabs-container {
          max-width: 800px;
          margin: 0 auto;
          display: flex;
          gap: 1.5rem;
          padding: 0 1.5rem;
        }

        .tab-btn {
          background: none;
          border: none;
          padding: 0.75rem 0;
          font-size: 1rem;
          font-weight: 600;
          color: #6b7280;
          cursor: pointer;
          border-bottom: 3px solid transparent;
          transition: all 0.2s;
        }
        .tab-btn:hover {
          color: #111827;
        }
        .tab-btn.active {
          color: var(--primary);
          border-bottom-color: var(--primary);
        }

        .main-content {
          max-width: 800px;
          margin: 0 auto;
          padding: 2rem 1.5rem 4rem;
        }

        .overall-progress-card {
           background: linear-gradient(135deg, #1e1b4b 0%, #4338ca 100%);
           border-radius: var(--radius-lg);
           padding: 1.75rem;
           box-shadow: 0 20px 25px -5px rgba(67, 56, 202, 0.2), 0 8px 10px -6px rgba(67, 56, 202, 0.2);
           color: white;
           margin-bottom: 2rem;
        }

        .percentage-display {
          font-size: 3rem;
          font-weight: 800;
          line-height: 1;
          color: #fff;
        }
        .percentage-display span {
          font-size: 1.5rem;
          color: rgba(255,255,255,0.7);
        }

        .progress-track-large {
          height: 12px;
          background: rgba(255,255,255,0.2);
          border-radius: 6px;
          overflow: hidden;
          margin-bottom: 0.75rem;
        }

        .progress-fill-gradient {
          height: 100%;
          background: linear-gradient(90deg, #34d399 0%, #10b981 100%);
          border-radius: 6px;
          transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .progress-stats {
          display: flex;
          justify-content: space-between;
          font-size: 0.85rem;
          font-weight: 500;
          color: rgba(255,255,255,0.8);
        }

        .title-md { margin: 0; font-size: 1.25rem; font-weight: 700; }
        .subtitle { margin: 0; font-size: 0.85rem; margin-top: 4px; }
        .section-title { margin: 0 0 1rem 0; font-size: 1.15rem; font-weight: 700; color: #1f2937; }

        .cards-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 1.25rem;
        }

        .subject-card {
          background: var(--bg-card);
          border-radius: var(--radius-md);
          padding: 1.25rem;
          box-shadow: var(--shadow-sm);
          transition: transform 0.2s, box-shadow 0.2s;
        }
        .subject-card.interactive:hover {
          transform: translateY(-2px);
          box-shadow: var(--shadow-md);
        }

        .icon-large { font-size: 1.75rem; margin-right: 0.75rem; }
        .subject-name { font-size: 1.1rem; font-weight: 700; }
        
        .prog-percent {
          font-size: 0.8rem;
          font-weight: 700;
          padding: 3px 8px;
          border-radius: 12px;
        }

        .progress-track-small {
          height: 6px;
          background: #f3f4f6;
          border-radius: 3px;
          overflow: hidden;
        }
        .progress-fill { height: 100%; transition: width 0.7s ease-out; }

        .next-lesson-box {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 10px;
          padding: 1rem;
        }

        .next-badge {
          display: inline-block;
          font-size: 0.65rem;
          font-weight: 800;
          color: #ef4444;
          background: #fee2e2;
          padding: 2px 6px;
          border-radius: 4px;
          margin-bottom: 6px;
          letter-spacing: 0.05em;
        }

        .lesson-title {
          font-size: 0.95rem;
          font-weight: 600;
          color: #111827;
          line-height: 1.4;
        }

        .lesson-meta {
          font-size: 0.75rem;
          color: #6b7280;
          font-weight: 500;
        }

        .btn-done-small {
          color: white;
          border: none;
          padding: 6px 14px;
          border-radius: 8px;
          font-size: 0.8rem;
          font-weight: 600;
          cursor: pointer;
          transition: opacity 0.2s, transform 0.1s;
        }
        .btn-done-small:hover:not(:disabled) { opacity: 0.9; transform: scale(1.02); }
        .btn-done-small:disabled { opacity: 0.5; cursor: not-allowed; }

        .completed-box {
          text-align: center;
          color: #9ca3af;
          font-size: 0.85rem;
          font-weight: 600;
          padding: 1rem 0;
          background: #f9fafb;
          border-radius: 10px;
        }

        /* List View */
        .list-container {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .list-item-card {
          background: white;
          border-radius: var(--radius-md);
          padding: 1rem 1.25rem;
          box-shadow: var(--shadow-sm);
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .icon-wrapper {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.5rem;
          flex-shrink: 0;
        }

        .list-content {
          flex: 1;
          min-width: 0;
        }

        .badge {
          color: white;
          padding: 2px 8px;
          border-radius: 6px;
          font-size: 0.7rem;
          font-weight: 700;
        }

        .meta-text { font-size: 0.8rem; font-weight: 600; color: #4b5563; }
        .meta-date { font-size: 0.75rem; color: #9ca3af; }

        .item-title {
          font-size: 1rem;
          font-weight: 700;
          color: #111827;
          margin-bottom: 2px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .item-subtitle {
          font-size: 0.8rem;
          color: #6b7280;
        }

        .btn-done {
          padding: 0.6rem 1.25rem;
          border: none;
          border-radius: 10px;
          color: white;
          font-weight: 700;
          font-size: 0.85rem;
          cursor: pointer;
          transition: all 0.2s;
          flex-shrink: 0;
        }
        .btn-done:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .btn-done:disabled { opacity: 0.6; cursor: not-allowed; }

        /* Actions View */
        .action-card {
          border-radius: var(--radius-md);
          padding: 1.5rem;
          box-shadow: var(--shadow-sm);
        }
        .action-label {
          display: block;
          font-size: 0.85rem;
          font-weight: 600;
          color: #4b5563;
          margin-bottom: 0.5rem;
        }

        .btn-chip {
          background: #f3f4f6;
          border: 1px solid #e5e7eb;
          color: #4b5563;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          font-weight: 600;
          font-size: 0.85rem;
          cursor: pointer;
          transition: all 0.2s;
        }
        .btn-chip.active { background: #111827; color: white; border-color: #111827; }
        
        .date-input {
          width: 100%;
          padding: 0.75rem 1rem;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          font-family: inherit;
          font-size: 0.9rem;
        }

        .action-btn-card {
          background: white;
          border: 2px solid transparent;
          border-radius: var(--radius-md);
          padding: 1.5rem;
          text-align: center;
          transition: transform 0.2s;
        }
        .action-btn-card.dashed { border-style: dashed; }
        .action-btn-card:hover { transform: translateY(-2px); }
        
        .action-name { font-weight: 700; font-size: 1.1rem; }
        .action-desc { font-size: 0.8rem; color: #6b7280; margin-top: 4px; }
        
        .btn-outline {
          background: transparent;
          border: 1px solid #d1d5db;
          color: #374151;
          border-radius: 8px;
          padding: 0.6rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }
        .btn-outline:hover:not(:disabled) { background: #f3f4f6; }
        
        .btn-solid {
          color: white;
          border: none;
          border-radius: 8px;
          padding: 0.6rem;
          font-weight: 600;
          cursor: pointer;
          transition: transform 0.2s;
        }
        .btn-solid:hover:not(:disabled) { transform: scale(1.02); }

        .empty-state {
          text-align: center;
          padding: 3rem 1rem;
          color: #6b7280;
        }

        .loader-full {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 4rem 1rem;
          color: #6b7280;
          font-weight: 600;
        }

        .toast-message {
          position: fixed;
          bottom: 2rem;
          left: 50%;
          transform: translateX(-50%);
          background: #111827;
          color: white;
          padding: 1rem 1.5rem;
          border-radius: 12px;
          font-weight: 600;
          font-size: 0.9rem;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2);
          z-index: 1000;
          animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        .toast-error { background: #ef4444; }

      `}</style>
    </div>
  );
}
