import { useState, useCallback } from "react";

/* ═══════════════════════════════════════════
   PDF → Images (pdf.js via CDN)
═══════════════════════════════════════════ */
const loadPdfJs = () =>
  new Promise((resolve, reject) => {
    if (window.pdfjsLib) return resolve(window.pdfjsLib);
    const s = document.createElement("script");
    s.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
    s.onload = () => {
      window.pdfjsLib.GlobalWorkerOptions.workerSrc =
        "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
      resolve(window.pdfjsLib);
    };
    s.onerror = () => reject(new Error("pdf.js 로드 실패"));
    document.head.appendChild(s);
  });

const pdfToImages = async (file, scale = 2.0) => {
  const lib = await loadPdfJs();
  const pdf = await lib.getDocument({ data: await file.arrayBuffer() }).promise;
  const imgs = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const vp = page.getViewport({ scale });
    const canvas = document.createElement("canvas");
    canvas.width = vp.width;
    canvas.height = vp.height;
    await page.render({ canvasContext: canvas.getContext("2d"), viewport: vp }).promise;
    imgs.push(canvas.toDataURL("image/jpeg", 0.9).split(",")[1]);
  }
  return imgs;
};

/* ═══════════════════════════════════════════
   Claude API helper
═══════════════════════════════════════════ */
const claudeAPI = async ({ images = [], prompt, system = "" }) => {
  const content = [
    ...images.map((data) => ({
      type: "image",
      source: { type: "base64", media_type: "image/jpeg", data },
    })),
    { type: "text", text: prompt },
  ];
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 2000,
      ...(system ? { system } : {}),
      messages: [{ role: "user", content }],
    }),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.error?.message || `API 오류 (${res.status})`);
  }
  const d = await res.json();
  return d.content.map((b) => b.text || "").join("");
};

const safeJSON = (text) => {
  try {
    return JSON.parse(text.replace(/```json\n?|```\n?/g, "").trim());
  } catch {
    return null;
  }
};

const normalize = (s) =>
  String(s ?? "")
    .trim()
    .toLowerCase()
    .replace(/①/g, "1").replace(/②/g, "2").replace(/③/g, "3")
    .replace(/④/g, "4").replace(/⑤/g, "5")
    .replace(/\s+/g, "");

/* ═══════════════════════════════════════════
   Design tokens
═══════════════════════════════════════════ */
const C = {
  navy: "#1A2744",
  navyLight: "#243566",
  bg: "#F4F1EC",
  card: "#FFFFFF",
  green: "#2E6B45",
  greenBg: "#EAF4EE",
  red: "#B83232",
  redBg: "#FDECEA",
  yellow: "#D68910",
  yellowBg: "#FEF9E7",
  border: "#E2DBD0",
  muted: "#7A7066",
  text: "#1A2744",
};

const css = `
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Noto Sans KR', sans-serif; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
  .fadein { animation: fadeUp 0.35s ease both; }
  .spin { animation: spin 0.9s linear infinite; }
  .pulse { animation: pulse 1.4s ease infinite; }
  .card { background:${C.card}; border-radius:14px; box-shadow:0 2px 12px rgba(26,39,68,0.07); }
  .btn { border:none; border-radius:8px; padding:11px 22px; font-size:14px; font-weight:600; cursor:pointer; font-family:inherit; transition:all 0.18s; }
  .btn-primary { background:${C.navy}; color:#fff; }
  .btn-primary:hover:not(:disabled) { background:${C.navyLight}; }
  .btn-primary:disabled { background:#B8C0CC; cursor:not-allowed; }
  .btn-ghost { background:transparent; color:${C.navy}; border:1.5px solid ${C.navy}; }
  .btn-ghost:hover:not(:disabled) { background:#EEF1F8; }
  .btn-sm { padding:7px 14px; font-size:12px; border-radius:6px; }
  .drop-zone { border:2px dashed ${C.border}; border-radius:14px; padding:36px; text-align:center; cursor:pointer; transition:all 0.2s; background:#FAFAF8; }
  .drop-zone:hover, .drop-zone.drag { border-color:${C.navy}; background:#EEF1FA; }
  .tag { display:inline-block; border-radius:6px; padding:2px 8px; font-size:11px; font-weight:700; }
  input[type=text], input[type=number], select { font-family:inherit; font-size:13px; border:1.5px solid ${C.border}; border-radius:7px; padding:6px 10px; outline:none; transition:border-color 0.15s; }
  input[type=text]:focus, input[type=number]:focus, select:focus { border-color:${C.navy}; }
  tr:hover td { background:#FAFAF8; }
`;

/* ═══════════════════════════════════════════
   Main App
═══════════════════════════════════════════ */
export default function ExamGrader() {
  const [step, setStep] = useState(0);
  const [answerKey, setAnswerKey] = useState([]);
  const [students, setStudents] = useState([]);
  const [grading, setGrading] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [loadingMsg, setLoadingMsg] = useState("");
  const [globalError, setGlobalError] = useState("");

  /* ── Answer Key ── */
  const processAnswerKey = async (file) => {
    setGlobalError("");
    setLoadingMsg("PDF 변환 중...");
    try {
      const imgs = await pdfToImages(file);
      setLoadingMsg("AI가 답안지 분석 중...");
      const raw = await claudeAPI({
        images: imgs,
        prompt:
          "이 답안지에서 모든 문항의 번호, 정답, 배점, 유형을 추출하세요.\n" +
          "형식: [{\"num\":1,\"type\":\"objective\",\"answer\":\"①\",\"points\":2},...]\n" +
          "type은 objective(객관식) 또는 subjective(주관식)\n" +
          "객관식 정답은 ①②③④⑤ 표기 유지. 주관식은 모범답안 전체.\n" +
          "JSON만 출력하세요. 다른 텍스트 없이.",
        system:
          "한국 초등학교 시험 채점 보조 시스템. 지시된 JSON 형식만 출력하세요.",
      });
      const parsed = safeJSON(raw);
      if (!Array.isArray(parsed) || parsed.length === 0)
        throw new Error("답안지를 파싱하지 못했습니다. 더 선명한 스캔 파일을 사용해보세요.");
      setAnswerKey(parsed.map((q, i) => ({ ...q, _id: i })).sort((a, b) => a.num - b.num));
    } catch (e) {
      setGlobalError(e.message);
    } finally {
      setLoadingMsg("");
    }
  };

  const updateKey = (idx, field, val) =>
    setAnswerKey((prev) => prev.map((q, i) => (i === idx ? { ...q, [field]: val } : q)));

  const addKeyItem = () =>
    setAnswerKey((prev) => [
      ...prev,
      { num: prev.length + 1, type: "objective", answer: "", points: 2, _id: Date.now() },
    ]);

  /* ── Student Processing ── */
  const addStudentFiles = (files) => {
    const maxScore = answerKey.reduce((s, q) => s + (Number(q.points) || 0), 0);
    const news = Array.from(files)
      .filter((f) => f.name.toLowerCase().endsWith(".pdf"))
      .map((f) => ({
        id: Math.random().toString(36).slice(2),
        name: f.name.replace(/\.pdf$/i, ""),
        file: f,
        status: "pending",
        answers: [],
        totalScore: 0,
        maxScore,
        errorMsg: "",
      }));
    setStudents((p) => [...p, ...news]);
  };

  const gradeAll = async () => {
    setGrading(true);
    setGlobalError("");
    for (const student of students) {
      if (student.status === "done") continue;
      setStudents((p) =>
        p.map((s) => (s.id === student.id ? { ...s, status: "processing" } : s))
      );
      try {
        // 1. OCR
        const imgs = await pdfToImages(student.file);
        const ocrRaw = await claudeAPI({
          images: imgs,
          prompt:
            "이 학생 시험지에서 학생 이름과 각 문항의 답안을 추출하세요.\n" +
            "형식: {\"studentName\":\"이름(없으면 빈 문자열)\",\"answers\":[{\"num\":1,\"answer\":\"③\"}]}\n" +
            "손글씨를 최대한 판독하고 빈칸은 빈 문자열로. JSON만 출력.",
          system:
            "한국 초등학교 손글씨 시험지 답안 추출기. 최대한 정확히 판독하세요. JSON만 출력.",
        });
        const ocr = safeJSON(ocrRaw);
        if (!ocr) throw new Error("답안 추출 실패. 스캔 품질을 확인해주세요.");
        const studentName = (ocr.studentName || "").trim() || student.name;
        const studentAnswers = ocr.answers || [];

        // 2. Grade objective locally
        const graded = answerKey.map((q) => {
          const sa = studentAnswers.find((a) => a.num === q.num);
          const studentAns = sa?.answer || "";
          if (q.type === "objective") {
            const correct = normalize(studentAns) === normalize(q.answer);
            return {
              num: q.num, type: "objective",
              studentAnswer: studentAns, modelAnswer: q.answer,
              correct, earned: correct ? Number(q.points) : 0, maxPoints: Number(q.points),
            };
          }
          return {
            num: q.num, type: "subjective",
            studentAnswer: studentAns, modelAnswer: q.answer,
            correct: null, earned: null, maxPoints: Number(q.points),
          };
        });

        // 3. Grade subjective via Claude
        const subj = graded.filter((g) => g.type === "subjective");
        if (subj.length > 0) {
          const subjPrompt =
            "다음 주관식 답안을 채점하세요.\n\n" +
            subj.map((g) =>
              `【${g.num}번 | 배점:${g.maxPoints}점】\n모범: ${g.modelAnswer}\n학생: ${g.studentAnswer || "(무응답)"}`
            ).join("\n\n") +
            "\n\n핵심 내용 포함 시 정답. 부분 점수 가능.\n" +
            "결과: [{\"num\":번호,\"earned\":획득점수,\"correct\":true/false,\"reason\":\"간단한 이유\"},...]\nJSON만 출력.";
          const subjRaw = await claudeAPI({
            prompt: subjPrompt,
            system: "초등학교 주관식 채점기. JSON만 출력하세요.",
          });
          const subjGrades = safeJSON(subjRaw) || [];
          subjGrades.forEach((g) => {
            const idx = graded.findIndex((a) => a.num === g.num);
            if (idx >= 0) Object.assign(graded[idx], { earned: g.earned, correct: g.correct, reason: g.reason });
          });
        }

        const totalScore = graded.reduce((s, a) => s + (a.earned || 0), 0);
        setStudents((p) =>
          p.map((s) =>
            s.id === student.id
              ? { ...s, name: studentName, status: "done", answers: graded, totalScore }
              : s
          )
        );
      } catch (e) {
        setStudents((p) =>
          p.map((s) =>
            s.id === student.id ? { ...s, status: "error", errorMsg: e.message } : s
          )
        );
      }
    }
    setGrading(false);
    if (students.some((s) => s.status === "done" || students.find((x) => x.status !== "error")))
      setStep(2);
  };

  /* ── Analysis File ── */
  const handleAnalysisFile = async (file) => {
    try {
      const text = await file.text();
      setAnalysisData(JSON.parse(text));
    } catch {
      setGlobalError("분석 파일을 읽지 못했습니다. JSON 형식인지 확인하세요.");
    }
  };

  /* ── Download Report ── */
  const downloadReport = (s) => {
    const analysis = analysisData?.students?.find((x) => x.name === s.name);
    const pct = s.maxScore ? Math.round((s.totalScore / s.maxScore) * 100) : 0;
    const html = `<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<title>${s.name} 채점 결과</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
<style>
  body{font-family:'Noto Sans KR',sans-serif;max-width:800px;margin:40px auto;color:#1A2744;padding:20px}
  h1{font-size:24px;border-bottom:3px solid #1A2744;padding-bottom:12px;margin-bottom:20px}
  .meta{display:flex;gap:32px;margin-bottom:24px}
  .score{font-size:52px;font-weight:700;color:${pct>=60?"#2E6B45":"#B83232"};line-height:1}
  .sub{font-size:14px;color:#888;margin-top:4px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{background:#1A2744;color:white;padding:10px 12px;text-align:left}
  td{padding:9px 12px;border-bottom:1px solid #f0ede8}
  .ok{color:#2E6B45;font-weight:700} .no{color:#B83232;font-weight:700}
  .note{background:#f7f9fe;border-left:4px solid #1A2744;padding:16px;margin-top:28px;border-radius:4px}
  @media print{button{display:none}}
</style></head><body>
<h1>📋 채점 결과</h1>
<div class="meta">
  <div><div class="score">${s.totalScore}</div><div class="sub">/ ${s.maxScore}점</div></div>
  <div style="margin-top:8px"><strong style="font-size:18px">${s.name}</strong><br>
  <span style="color:#888;font-size:13px">정답률 ${pct}% &nbsp;·&nbsp; ${s.answers.filter(a=>a.correct).length}/${s.answers.length} 정답</span></div>
</div>
<button onclick="window.print()" style="margin-bottom:20px;padding:8px 18px;background:#1A2744;color:white;border:none;border-radius:6px;cursor:pointer;font-size:13px">🖨️ 인쇄</button>
<table>
  <tr><th>문항</th><th>유형</th><th>정답</th><th>학생 답안</th><th>결과</th><th>점수</th>${analysis?"<th>분석</th>":""}</tr>
  ${s.answers.map(a=>{
    const ai = analysis?.analysis?.find(x=>x.questionNum===a.num);
    return `<tr>
      <td>${a.num}번</td>
      <td style="color:#888">${a.type==="objective"?"객관식":"주관식"}</td>
      <td class="ok">${a.modelAnswer?.length>25?a.modelAnswer.slice(0,25)+"…":a.modelAnswer}</td>
      <td>${a.studentAnswer||"<span style='color:#ccc'>무응답</span>"}</td>
      <td class="${a.correct?"ok":"no"}">${a.correct?"✓ 정답":"✗ 오답"}</td>
      <td>${a.earned??0}/${a.maxPoints}점</td>
      ${analysis?`<td style="font-size:12px;color:#555">${ai?ai.recommendation||ai.errorType||"":""}</td>`:""}
    </tr>`;
  }).join("")}
</table>
${s.answers.some(a=>a.reason)?`<div class="note"><strong>📝 채점 메모</strong><br><br>${s.answers.filter(a=>a.reason).map(a=>`<div style="margin-bottom:6px">• <strong>${a.num}번:</strong> ${a.reason}</div>`).join("")}</div>`:""}
${analysis&&analysis.analysis?.length?`<div class="note" style="margin-top:16px;border-left-color:#D68910"><strong>🔍 학습 분석 (외부 AI)</strong><br><br>${analysis.analysis.map(a=>`<div style="margin-bottom:8px">• <strong>${a.questionNum}번 - ${a.errorType||""}:</strong> ${a.recommendation||""}</div>`).join("")}</div>`:""}
</body></html>`;
    const url = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
    Object.assign(document.createElement("a"), { href: url, download: `${s.name}_채점결과.html` }).click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const maxScore = answerKey.reduce((s, q) => s + (Number(q.points) || 0), 0);
  const done = students.filter((s) => s.status === "done");

  return (
    <div style={{ fontFamily: "'Noto Sans KR', sans-serif", minHeight: "100vh", background: C.bg, color: C.text }}>
      <style>{css}</style>
      <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet" />

      {/* Header */}
      <header style={{ background: C.navy, color: "#fff", padding: "18px 40px", display: "flex", alignItems: "center", gap: 14, boxShadow: "0 2px 12px rgba(0,0,0,0.15)" }}>
        <div style={{ fontSize: 30 }}>✏️</div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 19, letterSpacing: "-0.3px" }}>AI 시험 채점기</div>
          <div style={{ fontSize: 12, opacity: 0.6, marginTop: 2 }}>스캔된 손글씨 시험지 자동 채점 시스템</div>
        </div>
      </header>

      {/* Step Tabs */}
      <div style={{ background: "#fff", borderBottom: `1px solid ${C.border}`, padding: "0 40px", display: "flex" }}>
        {["① 답안지 설정", "② 학생 채점", "③ 결과 확인"].map((label, i) => {
          const active = step === i;
          const done_ = step > i;
          return (
            <button key={i} onClick={() => i < step && setStep(i)}
              style={{ padding: "15px 22px", border: "none", background: "transparent", borderBottom: active ? `3px solid ${C.navy}` : done_ ? `3px solid ${C.green}` : "3px solid transparent", color: active ? C.navy : done_ ? C.green : "#aaa", fontWeight: active ? 700 : 400, cursor: i < step ? "pointer" : "default", fontSize: 13.5, fontFamily: "inherit", letterSpacing: "-0.2px" }}>
              {done_ ? "✓ " : ""}{label}
            </button>
          );
        })}
      </div>

      <main style={{ maxWidth: 920, margin: "0 auto", padding: "32px 24px" }}>
        {/* Global Error */}
        {globalError && (
          <div className="fadein" style={{ background: C.redBg, border: `1px solid #f5c6cb`, borderRadius: 10, padding: "14px 18px", marginBottom: 22, color: C.red, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>⚠️ {globalError}</span>
            <button onClick={() => setGlobalError("")} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 20, color: C.red, lineHeight: 1 }}>×</button>
          </div>
        )}
        {/* Loading */}
        {loadingMsg && (
          <div className="fadein" style={{ background: "#EEF1FA", border: `1px solid #c5d3f5`, borderRadius: 10, padding: "14px 18px", marginBottom: 22, color: C.navy, display: "flex", alignItems: "center", gap: 12 }}>
            <div className="spin" style={{ width: 18, height: 18, border: `3px solid ${C.navy}`, borderTopColor: "transparent", borderRadius: "50%", flexShrink: 0 }} />
            <span style={{ fontSize: 14 }}>{loadingMsg}</span>
          </div>
        )}

        {/* ─── STEP 0: Answer Key ─── */}
        {step === 0 && (
          <div className="fadein">
            <h2 style={{ fontSize: 21, marginBottom: 6, fontWeight: 700 }}>답안지 설정</h2>
            <p style={{ color: C.muted, fontSize: 14, marginBottom: 24 }}>답안지 PDF를 업로드하면 AI가 문항별 정답과 배점을 자동 추출합니다. 추출 후 직접 수정할 수 있습니다.</p>

            {answerKey.length === 0 ? (
              <DropZone icon="📄" title="답안지 PDF 업로드" sub="드래그하거나 클릭하여 선택" multiple={false}
                onFiles={(files) => files[0] && processAnswerKey(files[0])} disabled={!!loadingMsg} />
            ) : (
              <div className="card fadein" style={{ padding: 24 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
                  <div style={{ fontWeight: 700, fontSize: 16 }}>📋 답안 목록 <span style={{ color: C.muted, fontWeight: 400, fontSize: 13 }}>({answerKey.length}문항 · 총 {maxScore}점)</span></div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button className="btn btn-ghost btn-sm" onClick={() => { setAnswerKey([]); document.getElementById("ak-in").click(); }}>다시 업로드</button>
                    <button className="btn btn-ghost btn-sm" onClick={addKeyItem}>+ 문항 추가</button>
                    <input id="ak-in" type="file" accept=".pdf" hidden onChange={(e) => e.target.files[0] && processAnswerKey(e.target.files[0])} />
                  </div>
                </div>

                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ background: C.bg }}>
                        {["문항", "유형", "정답", "배점(점)", ""].map((h) => (
                          <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontSize: 12, color: C.muted, fontWeight: 600, borderBottom: `1px solid ${C.border}` }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {answerKey.map((q, idx) => (
                        <tr key={q._id ?? idx}>
                          <td style={{ padding: "8px 12px", borderBottom: `1px solid #F3EEE8` }}>
                            <input type="number" value={q.num} onChange={(e) => updateKey(idx, "num", Number(e.target.value))} style={{ width: 52 }} />
                          </td>
                          <td style={{ padding: "8px 12px", borderBottom: `1px solid #F3EEE8` }}>
                            <select value={q.type} onChange={(e) => updateKey(idx, "type", e.target.value)}>
                              <option value="objective">객관식</option>
                              <option value="subjective">주관식</option>
                            </select>
                          </td>
                          <td style={{ padding: "8px 12px", borderBottom: `1px solid #F3EEE8` }}>
                            <input type="text" value={q.answer} onChange={(e) => updateKey(idx, "answer", e.target.value)}
                              placeholder={q.type === "objective" ? "예: ③" : "모범답안"}
                              style={{ width: q.type === "objective" ? 64 : 260 }} />
                          </td>
                          <td style={{ padding: "8px 12px", borderBottom: `1px solid #F3EEE8` }}>
                            <input type="number" value={q.points} onChange={(e) => updateKey(idx, "points", Number(e.target.value))} style={{ width: 52 }} />
                          </td>
                          <td style={{ padding: "8px 12px", borderBottom: `1px solid #F3EEE8` }}>
                            <button onClick={() => setAnswerKey((p) => p.filter((_, i) => i !== idx))} style={{ background: "none", border: "none", cursor: "pointer", color: "#C0B8B0", fontSize: 16, lineHeight: 1 }}>✕</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end" }}>
                  <button className="btn btn-primary" onClick={() => setStep(1)}>다음 단계 →</button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ─── STEP 1: Students ─── */}
        {step === 1 && (
          <div className="fadein">
            <h2 style={{ fontSize: 21, marginBottom: 6, fontWeight: 700 }}>학생 시험지 채점</h2>
            <p style={{ color: C.muted, fontSize: 14, marginBottom: 24 }}>스캔된 학생 시험지 PDF를 업로드하세요. 여러 파일을 한 번에 선택할 수 있습니다.</p>

            <DropZone icon="🗂️" title="학생 시험지 PDF 업로드" sub="여러 파일 동시 선택 가능" multiple={true}
              onFiles={addStudentFiles} disabled={grading} />

            {students.length > 0 && (
              <div className="card fadein" style={{ padding: 24, marginTop: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                  <div style={{ fontWeight: 700, fontSize: 15 }}>학생 목록 ({students.length}명)</div>
                  {grading && (
                    <div style={{ fontSize: 13, color: C.navy, display: "flex", alignItems: "center", gap: 10 }}>
                      <div className="spin" style={{ width: 14, height: 14, border: `2.5px solid ${C.navy}`, borderTopColor: "transparent", borderRadius: "50%" }} />
                      채점 중... {students.filter((s) => s.status === "done").length}/{students.length}
                    </div>
                  )}
                </div>

                {students.map((s) => (
                  <StudentRow key={s.id} student={s} grading={grading}
                    onRemove={() => setStudents((p) => p.filter((x) => x.id !== s.id))} />
                ))}

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 20 }}>
                  <button className="btn btn-ghost" onClick={() => setStep(0)} disabled={grading}>← 이전</button>
                  <button className="btn btn-primary" onClick={gradeAll}
                    disabled={grading || students.length === 0 || students.every((s) => s.status === "done")}>
                    {grading ? "채점 중..." : `🚀 채점 시작 (${students.filter((s) => s.status !== "done").length}명)`}
                  </button>
                </div>
              </div>
            )}

            {students.length === 0 && (
              <div style={{ marginTop: 20 }}>
                <button className="btn btn-ghost" onClick={() => setStep(0)}>← 이전</button>
              </div>
            )}
          </div>
        )}

        {/* ─── STEP 2: Results ─── */}
        {step === 2 && (
          <ResultsStep
            students={students}
            answerKey={answerKey}
            analysisData={analysisData}
            onAnalysisUpload={handleAnalysisFile}
            onDownload={downloadReport}
            onBack={() => setStep(1)}
            globalError={globalError}
          />
        )}
      </main>
    </div>
  );
}

/* ═══════════════════════════════════════════
   Sub-components
═══════════════════════════════════════════ */

function DropZone({ icon, title, sub, multiple, onFiles, disabled }) {
  const [drag, setDrag] = useState(false);
  const id = `dz-${Math.random().toString(36).slice(2)}`;
  return (
    <label htmlFor={id}>
      <div className={`drop-zone ${drag ? "drag" : ""}`}
        onDrop={(e) => { e.preventDefault(); setDrag(false); if (!disabled) onFiles(e.dataTransfer.files); }}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        style={{ cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1 }}>
        <div style={{ fontSize: 38, marginBottom: 10 }}>{icon}</div>
        <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>{title}</div>
        <div style={{ fontSize: 13, color: "#999" }}>{sub}</div>
      </div>
      <input id={id} type="file" accept=".pdf" multiple={multiple} hidden
        disabled={disabled} onChange={(e) => onFiles(e.target.files)} />
    </label>
  );
}

function StudentRow({ student: s, grading, onRemove }) {
  const STATUS = {
    pending: { color: "#C0B8B0", label: "대기" },
    processing: { color: C.navy, label: "분석 중..." },
    done: { color: C.green, label: "완료" },
    error: { color: C.red, label: "오류" },
  };
  const st = STATUS[s.status];
  const pct = s.maxScore ? Math.round((s.totalScore / s.maxScore) * 100) : 0;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "11px 0", borderBottom: `1px solid #F3EEE8` }}>
      {s.status === "processing" ? (
        <div className="spin" style={{ width: 13, height: 13, border: `2.5px solid ${C.navy}`, borderTopColor: "transparent", borderRadius: "50%", flexShrink: 0 }} />
      ) : (
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: st.color, flexShrink: 0 }} />
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 500, fontSize: 14 }}>{s.name}</div>
        {s.errorMsg && <div style={{ fontSize: 12, color: C.red, marginTop: 2 }}>{s.errorMsg}</div>}
      </div>
      <div style={{ fontSize: 12, color: st.color, fontWeight: 600 }}>{st.label}</div>
      {s.status === "done" && (
        <div style={{ textAlign: "right" }}>
          <div style={{ fontWeight: 700, fontSize: 15, color: pct >= 60 ? C.green : C.red }}>{s.totalScore}<span style={{ fontWeight: 400, fontSize: 12, color: C.muted }}>/{s.maxScore}점</span></div>
        </div>
      )}
      {s.status !== "processing" && !grading && (
        <button onClick={onRemove} style={{ background: "none", border: "none", cursor: "pointer", color: "#D0C8C0", fontSize: 15, padding: "2px 4px" }}>✕</button>
      )}
    </div>
  );
}

function ResultsStep({ students, answerKey, analysisData, onAnalysisUpload, onDownload, onBack }) {
  const [sel, setSel] = useState(null);
  const done = students.filter((s) => s.status === "done");
  const avg = done.length ? Math.round(done.reduce((s, st) => s + st.totalScore, 0) / done.length) : 0;
  const maxScore = done[0]?.maxScore || 100;
  const hi = done.length ? Math.max(...done.map((s) => s.totalScore)) : 0;
  const lo = done.length ? Math.min(...done.map((s) => s.totalScore)) : 0;

  return (
    <div className="fadein">
      <h2 style={{ fontSize: 21, marginBottom: 6, fontWeight: 700 }}>채점 결과</h2>
      <p style={{ color: C.muted, fontSize: 14, marginBottom: 24 }}>{done.length}명 채점 완료</p>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 24 }}>
        {[
          { label: "채점 인원", val: `${done.length}명`, color: C.navy },
          { label: "평균 점수", val: `${avg}점`, color: avg >= 60 ? C.green : C.red },
          { label: "최고 점수", val: `${hi}점`, color: C.green },
          { label: "최저 점수", val: `${lo}점`, color: lo < 60 ? C.red : C.navy },
        ].map((s) => (
          <div key={s.label} className="card" style={{ padding: "18px 16px", textAlign: "center" }}>
            <div style={{ fontSize: 26, fontWeight: 700, color: s.color }}>{s.val}</div>
            <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Analysis Upload */}
      <div className="card" style={{ padding: "16px 20px", marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>🔍 외부 분석 파일 병합 <span style={{ fontSize: 12, color: C.muted, fontWeight: 400 }}>(선택)</span></div>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 3 }}>다른 AI가 생성한 JSON 분석 파일을 업로드하면 결과지에 포함됩니다</div>
        </div>
        <label style={{ cursor: "pointer" }}>
          <div className={`btn btn-ghost btn-sm ${analysisData ? "" : ""}`} style={{ whiteSpace: "nowrap", color: analysisData ? C.green : undefined, borderColor: analysisData ? C.green : undefined }}>
            {analysisData ? "✓ 병합됨" : "파일 선택"}
          </div>
          <input type="file" accept=".json" hidden onChange={(e) => e.target.files[0] && onAnalysisUpload(e.target.files[0])} />
        </label>
      </div>

      {/* Table */}
      <div className="card" style={{ overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: C.navy, color: "#fff" }}>
              {["이름", "점수", "정답/문항", "정답률", "문항별 결과", ""].map((h) => (
                <th key={h} style={{ padding: "12px 16px", textAlign: "left", fontSize: 13, fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {students.map((s) => {
              const correct = s.answers.filter((a) => a.correct).length;
              const pct = s.maxScore ? Math.round((s.totalScore / s.maxScore) * 100) : 0;
              const statusTag = {
                pending: { bg: "#f0ede8", color: C.muted, label: "대기" },
                processing: { bg: "#eef1fa", color: C.navy, label: "처리 중" },
                done: null,
                error: { bg: C.redBg, color: C.red, label: "오류" },
              }[s.status];

              return (
                <tr key={s.id} style={{ borderBottom: `1px solid #F3EEE8`, cursor: s.status === "done" ? "pointer" : "default" }}
                  onClick={() => s.status === "done" && setSel(s)}>
                  <td style={{ padding: "14px 16px", fontWeight: 500 }}>{s.name}</td>
                  <td style={{ padding: "14px 16px" }}>
                    {statusTag ? (
                      <span className="tag" style={{ background: statusTag.bg, color: statusTag.color }}>{statusTag.label}</span>
                    ) : (
                      <span style={{ fontWeight: 700, color: pct >= 60 ? C.green : C.red, fontSize: 15 }}>{s.totalScore}<span style={{ color: C.muted, fontWeight: 400, fontSize: 12 }}>/{s.maxScore}</span></span>
                    )}
                  </td>
                  <td style={{ padding: "14px 16px", color: C.muted, fontSize: 13 }}>{s.status === "done" ? `${correct}/${s.answers.length}` : "—"}</td>
                  <td style={{ padding: "14px 16px" }}>
                    {s.status === "done" && (
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{ width: 64, height: 7, background: C.border, borderRadius: 4 }}>
                          <div style={{ width: `${pct}%`, height: "100%", background: pct >= 60 ? C.green : C.red, borderRadius: 4 }} />
                        </div>
                        <span style={{ fontSize: 12, color: C.muted }}>{pct}%</span>
                      </div>
                    )}
                  </td>
                  <td style={{ padding: "14px 16px" }}>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
                      {s.answers.map((a) => (
                        <span key={a.num} title={`${a.num}번`} style={{ fontSize: 13, color: a.correct ? C.green : C.red, lineHeight: 1 }}>
                          {a.correct ? "●" : "○"}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td style={{ padding: "14px 16px" }}>
                    {s.status === "done" && (
                      <button onClick={(e) => { e.stopPropagation(); onDownload(s); }}
                        style={{ background: "none", border: `1px solid ${C.border}`, borderRadius: 7, padding: "5px 12px", fontSize: 12, cursor: "pointer", color: C.muted, fontFamily: "inherit" }}>
                        ↓ 결과지
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 20 }}>
        <button className="btn btn-ghost" onClick={onBack}>← 이전</button>
      </div>

      {/* Detail Modal */}
      {sel && <DetailModal student={sel} analysisData={analysisData} onClose={() => setSel(null)} onDownload={onDownload} />}
    </div>
  );
}

function DetailModal({ student: s, analysisData, onClose, onDownload }) {
  const analysis = analysisData?.students?.find((x) => x.name === s.name);
  const pct = s.maxScore ? Math.round((s.totalScore / s.maxScore) * 100) : 0;

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(10,20,50,0.55)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200, padding: 20 }}
      onClick={onClose}>
      <div className="card fadein" style={{ width: "100%", maxWidth: 700, maxHeight: "88vh", overflow: "auto", padding: 32, borderRadius: 18 }}
        onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 22 }}>
          <div>
            <h3 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>{s.name}</h3>
            <div style={{ marginTop: 6, display: "flex", gap: 16, alignItems: "center" }}>
              <span style={{ fontSize: 28, fontWeight: 700, color: pct >= 60 ? C.green : C.red }}>{s.totalScore}</span>
              <span style={{ fontSize: 14, color: C.muted }}>/ {s.maxScore}점 · 정답률 {pct}%</span>
            </div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 26, cursor: "pointer", color: "#B0A89E", lineHeight: 1 }}>×</button>
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: C.bg }}>
              {["문항", "유형", "정답", "학생 답안", "결과", "점수"].map((h) => (
                <th key={h} style={{ padding: "9px 12px", textAlign: "left", color: C.muted, fontWeight: 600, fontSize: 12, borderBottom: `1px solid ${C.border}` }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {s.answers.map((a) => (
              <tr key={a.num} style={{ borderBottom: `1px solid #F5F0EA` }}>
                <td style={{ padding: "10px 12px", fontWeight: 600 }}>{a.num}번</td>
                <td style={{ padding: "10px 12px" }}>
                  <span className="tag" style={{ background: a.type === "objective" ? "#EEF1FA" : C.yellowBg, color: a.type === "objective" ? C.navy : C.yellow }}>
                    {a.type === "objective" ? "객관" : "주관"}
                  </span>
                </td>
                <td style={{ padding: "10px 12px", color: C.green, fontWeight: 500, maxWidth: 140, wordBreak: "break-all" }}>
                  {a.modelAnswer?.length > 18 ? a.modelAnswer.slice(0, 18) + "…" : a.modelAnswer}
                </td>
                <td style={{ padding: "10px 12px", maxWidth: 140, wordBreak: "break-all" }}>
                  {a.studentAnswer || <span style={{ color: "#C0B8B0" }}>무응답</span>}
                </td>
                <td style={{ padding: "10px 12px" }}>
                  <span style={{ fontSize: 17 }}>{a.correct === true ? "✅" : a.correct === false ? "❌" : "⏳"}</span>
                </td>
                <td style={{ padding: "10px 12px", fontWeight: 600, color: a.correct ? C.green : C.red }}>
                  {a.earned ?? 0}/{a.maxPoints}점
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {s.answers.some((a) => a.reason) && (
          <div style={{ marginTop: 18, background: "#F0F4FC", borderRadius: 10, padding: 16 }}>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 10 }}>📝 주관식 채점 메모</div>
            {s.answers.filter((a) => a.reason).map((a) => (
              <div key={a.num} style={{ fontSize: 13, marginBottom: 6, color: C.text }}>
                <strong>{a.num}번:</strong> {a.reason}
              </div>
            ))}
          </div>
        )}

        {analysis?.analysis?.length > 0 && (
          <div style={{ marginTop: 14, background: C.yellowBg, borderRadius: 10, padding: 16, borderLeft: `4px solid ${C.yellow}` }}>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 10 }}>🔍 외부 AI 학습 분석</div>
            {analysis.analysis.map((a, i) => (
              <div key={i} style={{ fontSize: 13, marginBottom: 7 }}>
                <strong>{a.questionNum}번 {a.errorType ? `[${a.errorType}]` : ""}:</strong> {a.recommendation || ""}
              </div>
            ))}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 22 }}>
          <button className="btn btn-ghost" onClick={onClose}>닫기</button>
          <button className="btn btn-primary" onClick={() => onDownload(s)}>↓ 결과지 다운로드</button>
        </div>
      </div>
    </div>
  );
}
