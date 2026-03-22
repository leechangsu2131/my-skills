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
  const [loadingMsg, setLoadingMsg] = useState("백엔드 연동 중...");
  
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
    setLoadingMsg("서버에서 시트 데이터 연동 중...");
    try {
      const res = await fetch(`${API_BASE}/dashboard`);
      if (!res.ok) throw new Error("서버 응답 오류 (Python 서버 확인 필요)");
      const data = await res.json();
      
      setViews(data.views || []);
      setSubjects(data.subjects || []);
      
      setActiveTab(current => (data.views.find(v => v.id === current) ? current : (data.views[0]?.id || "")));
    } catch (e) {
      showToast("데이터 로드 실패: " + e.message, "error");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

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
      
      showToast(`📅 ${subj} 일정 ${days}일 밀기 완료`);
      await loadData();
    } catch (e) {
      showToast("밀기 실패: " + e.message, "error");
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
      
      showToast(`⏳ ${subj} 한 차시 연장 성공!`);
      await loadData();
    } catch (e) {
      showToast("연장 실패: " + e.message, "error");
    }
    setPushSubject(null);
  };

  const ScheduleCard = ({ item }) => {
    const color = SUBJECT_COLORS[item.과목] || { bg: "#F5F5F5", accent: "#666", icon: "📚" };
    const rowId = item._row || item.행번호;
    
    return (
      <div style={{
        background: color.bg, borderRadius: 16, padding: "18px 20px", display: "flex", alignItems: "center", gap: 16,
        border: `1.5px solid ${color.accent}22`, overflow: "hidden",
      }}>
        <div style={{
          width: 48, height: 48, borderRadius: 12, background: color.accent + "22",
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, flexShrink: 0
        }}>{color.icon}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{
              background: color.accent, color: "#fff", padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 700
            }}>{item.과목}</span>
            <span style={{ fontSize: 12, color: "#888" }}>{item.차시}차시</span>
            {item.계획일 && <span style={{ fontSize: 11, color: "#bbb" }}>({item.계획일})</span>}
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#1a1a2e", lineHeight: 1.4 }}>{item.수업내용}</div>
          <div style={{ fontSize: 12, color: "#666", marginTop: 2 }}>{item.대단원}</div>
        </div>
        <button
          onClick={() => markDone(item)}
          disabled={marking === rowId}
          style={{
            background: marking === rowId ? "#ccc" : color.accent,
            color: "#fff", border: "none", borderRadius: 10, padding: "8px 14px", fontSize: 12, fontWeight: 600,
            cursor: marking === rowId ? "not-allowed" : "pointer", flexShrink: 0, transition: "all 0.2s"
          }}
        >
          {marking === rowId ? "처리중..." : "완료 ✓"}
        </button>
      </div>
    );
  };

  const NextClassCard = ({ subject, data }) => {
    const color = SUBJECT_COLORS[subject] || { bg: "#F5F5F5", accent: "#666", icon: "📚" };
    const nextCls = data?.next;
    const recent = data?.recent;

    return (
      <div style={{ background: "#fff", borderRadius: 16, padding: "16px 18px", border: `2px solid ${color.accent}33` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
          <span style={{ fontSize: 20 }}>{color.icon}</span>
          <span style={{ fontWeight: 700, color: color.accent, fontSize: 15 }}>{subject}</span>
        </div>
        
        {recent && (
          <div style={{ marginBottom: 12, padding: "8px", background: "#f8f9fa", borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: "#888", marginBottom: 2 }}>✅ 직전 완료</div>
            <div style={{ fontSize: 13, fontWeight: 500, color: "#333" }}>{recent.차시}차시: {recent.수업내용}</div>
            <span style={{fontSize:10, color:"#bbb"}}>{recent.계획일}</span>
          </div>
        )}

        {nextCls ? (
          <div style={{ padding: "8px", background: color.bg, borderRadius: 8, marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: color.accent, fontWeight: 600, marginBottom: 2 }}>🎯 다음 목표</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#1a1a2e" }}>{nextCls.차시}차시: {nextCls.수업내용}</div>
            <span style={{fontSize:10, color:"#666"}}>{nextCls.계획일}</span>
          </div>
        ) : (
           <div style={{ fontSize: 13, color: "#aaa", marginBottom: 10 }}>모든 진도 완료! 🎉</div>
        )}
      </div>
    );
  };

  const renderViewContent = (view) => {
    if (view.type === "lesson_list") {
      return view.data.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px 20px", background: "#fff", borderRadius: 20, color: "#999", fontSize: 14 }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🎉</div>
          선택한 기간의 미완료 개설 수업이 없습니다.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {view.data.map((item, i) => <ScheduleCard key={i} item={item} />)}
        </div>
      );
    }
    
    if (view.type === "next_class_grid") {
      return (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
          {Object.keys(view.data).map(sub => (
            <NextClassCard key={sub} subject={sub} data={view.data[sub]} />
          ))}
        </div>
      );
    }

    if (view.type === "progress_list") {
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {Object.entries(view.data).map(([sub, p]) => {
             const color = SUBJECT_COLORS[sub] || { accent: "#3B7DD8" };
             return (
               <div key={sub} style={{ background: "#fff", padding: "16px", borderRadius: 16, border: `1px solid #eee` }}>
                 <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <span style={{ fontWeight: 700 }}>{sub}</span>
                    <span style={{ fontWeight: 700, color: color.accent }}>{p.진도율}</span>
                 </div>
                 <div style={{ background: "#F0F0F0", height: 10, borderRadius: 5, overflow: "hidden" }}>
                    <div style={{ background: color.accent, height: "100%", width: p.진도율, transition: "width 0.5s ease-out" }} />
                 </div>
                 <div style={{ fontSize: 11, color: "#888", marginTop: 6, textAlign: "right" }}>
                    {p.완료} / {p.전체} 차시 완료
                 </div>
               </div>
             );
          })}
        </div>
      );
    }

    if (view.type === "push_action") {
      return (
        <div>
          <div style={{ background: "#fff", borderRadius: 16, padding: "16px 18px", marginBottom: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "#1a1a2e" }}>⚙️ 일괄 연기 옵션 설정</div>
            <div style={{ marginBottom: 8, fontSize: 12, color: "#666" }}>1. 며칠을 미룰까요?</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
              {[1, 3, 5, 7, 14].map(d => (
                <button
                  key={d} onClick={() => setPushDays(d)}
                  style={{ background: pushDays === d ? "#1a1a2e" : "#F5F5F5", color: pushDays === d ? "#fff" : "#666", border: "none", borderRadius: 10, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
                >{d}일</button>
              ))}
            </div>
            <div style={{ marginBottom: 8, fontSize: 12, color: "#666" }}>2. 언제부터 연기할까요? (비워두면 모든 미완료 건 밀기)</div>
            <input type="date" value={pushFrom} onChange={e => setPushFrom(e.target.value)} style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #ddd", fontSize: 13, width: "100%", outline: "none" }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {subjects.map(subject => {
              const color = SUBJECT_COLORS[subject] || { bg: "#F5F5F5", accent: "#666", icon: "📚" };
              return (
                <button
                  key={subject} onClick={() => pushSchedule(subject, pushDays, pushFrom)} disabled={pushSubject === subject}
                  style={{ background: pushSubject === subject ? "#F5F5F5" : color.bg, border: `1.5px solid ${color.accent}33`, borderRadius: 14, padding: "16px 20px", display: "flex", alignItems: "center", gap: 14, cursor: pushSubject === subject ? "not-allowed" : "pointer", textAlign: "left", width: "100%" }}
                >
                  <span style={{ fontSize: 24 }}>{color.icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, color: color.accent, fontSize: 14 }}>{subject} 연기하기</div>
                    <div style={{ fontSize: 12, color: "#888" }}>+{pushDays}일 {pushFrom ? `(${pushFrom} 이후)` : "(전체)"}</div>
                  </div>
                  <span style={{ background: color.accent, color: "#fff", borderRadius: 8, padding: "6px 12px", fontSize: 12, fontWeight: 700 }}>{pushSubject === subject ? "처리중..." : "연기 →"}</span>
                </button>
              );
            })}
          </div>
        </div>
      );
    }
    
    if (view.type === "extend_action") {
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: "16px", fontSize: 13, color: "#666", lineHeight: 1.5 }}>
            💡 수업 내용이 길어 한 시간이 초과될 경우, <b>현재 진행할 차시와 동일한 행을 시트 아래에 복제</b>하여 2시간 분량으로 시수를 늘립니다.
          </div>
          {subjects.map(subject => {
            const color = SUBJECT_COLORS[subject] || { bg: "#F5F5F5", accent: "#666", icon: "➕" };
            return (
              <button
                key={subject} onClick={() => extendSchedule(subject)} disabled={pushSubject === subject}
                style={{ background: "#fff", border: `2px dashed ${color.accent}55`, borderRadius: 14, padding: "16px", display: "flex", alignItems: "center", gap: 12, cursor: pushSubject === subject ? "not-allowed" : "pointer", width: "100%" }}
              >
                 <span style={{ fontSize: 24 }}>{color.icon}</span>
                 <div style={{ flex: 1, textAlign: "left" }}>
                   <div style={{ fontSize: 14, fontWeight: 700, color: "#1a1a2e" }}>{subject} 수업 연장</div>
                   <div style={{ fontSize: 12, color: "#888" }}>가장 최근 미완료 차시 1칸 복제 추가</div>
                 </div>
                 <span style={{ background: color.accent, color: "#fff", padding: "6px 12px", borderRadius: 8, fontSize: 12, fontWeight: 700 }}>{pushSubject === subject ? "처리중..." : "+ 연장"}</span>
              </button>
            )
          })}
        </div>
      );
    }

    return <div>지원되지 않는 뷰 타입: {view.type}</div>;
  };

  return (
    <div style={{ fontFamily: "'Noto Sans KR', sans-serif", background: "#F8F7F4", minHeight: "100vh", padding: "0 0 40px" }}>
      <div style={{ background: "#1a1a2e", padding: "24px 20px 0", position: "sticky", top: 0, zIndex: 100 }}>
        <div style={{ maxWidth: 540, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <div>
              <div style={{ color: "#fff", fontSize: 20, fontWeight: 800, letterSpacing: -0.5 }}>📚 스마트 진도표</div>
              <div style={{ color: "#888", fontSize: 12, marginTop: 2 }}>Python Backend Sync</div>
            </div>
            <button
              onClick={loadData} disabled={loading}
              style={{ background: "#ffffff18", color: "#fff", border: "1px solid #ffffff30", borderRadius: 10, padding: "8px 14px", fontSize: 12, cursor: loading ? "not-allowed" : "pointer" }}
            >{loading ? "⟳" : "새로고침"}</button>
          </div>

          <div style={{ display: "flex", gap: 6, overflowX: "auto", paddingBottom: 10, scrollbarWidth: "none" }}>
            {views.map(v => (
              <button
                key={v.id} onClick={() => setActiveTab(v.id)}
                style={{
                  background: activeTab === v.id ? "#fff" : "transparent", color: activeTab === v.id ? "#1a1a2e" : "#888",
                  border: "none", borderRadius: "10px 10px 0 0", padding: "10px 14px", fontSize: 13, fontWeight: activeTab === v.id ? 700 : 400,
                  cursor: "pointer", transition: "all 0.2s", whiteSpace: "nowrap", flexShrink: 0
                }}
              >
                {v.label}
                {v.type === "lesson_list" && v.data && v.data.length > 0 && (
                  <span style={{
                    background: activeTab === v.id ? "#E8724A" : "#555", color: "#fff", borderRadius: 10,
                    padding: "1px 6px", fontSize: 10, fontWeight: 700, marginLeft: 6
                  }}>{v.data.length}</span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 540, margin: "0 auto", padding: "20px 16px 0" }}>
        {loading && views.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 20px" }}>
            <div style={{ fontSize: 36, marginBottom: 16 }}>⟳</div>
            <div style={{ color: "#666", fontSize: 14 }}>{loadingMsg}</div>
          </div>
        ) : (
          views.map(view => view.id === activeTab && (
            <div key={view.id} style={{ animation: "fadeIn 0.3s ease" }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#555", marginBottom: 14 }}>{view.title}</div>
              {renderViewContent(view)}
            </div>
          ))
        )}
      </div>

      {toast && (
        <div style={{
          position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)",
          background: toast.type === "error" ? "#E53E3E" : "#1a1a2e", color: "#fff", borderRadius: 12,
          padding: "12px 20px", fontSize: 13, fontWeight: 600, boxShadow: "0 8px 40px rgba(0,0,0,0.2)",
          zIndex: 999, animation: "slideUp 0.3s ease", whiteSpace: "nowrap"
        }}>{toast.msg}</div>
      )}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;800&display=swap');
        @keyframes slideUp { from { opacity: 0; transform: translateX(-50%) translateY(20px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
        * { box-sizing: border-box; } button { outline: none; }
        ::-webkit-scrollbar { display: none; }
      `}</style>
    </div>
  );
}
