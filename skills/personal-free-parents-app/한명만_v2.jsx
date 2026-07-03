import { useState, useEffect, useRef } from "react";

// ─────────────────────────────────────────────────────────────
// 콘셉트: 한낮의 그늘 (Midday Shade)
// 감독하는 한 명은 "햇볕"(따뜻한 호박색) 안에 있고,
// 쉬는 부모들은 "그늘"(짙은 숲색) 안에 있다.
// 이 은유가 앱의 모든 색과 레이아웃을 결정한다.
// ─────────────────────────────────────────────────────────────
const T = {
  // 햇볕 영역 (감독, 액션)
  parchment:  "#F6EFD8",   // 따뜻한 양피지 — 배경
  amber:      "#C07A22",   // 오후 햇살 — 주 액션
  amberGlow:  "#EDD49A",   // 햇살 번짐
  amberPale:  "#FAF4E4",   // 거의 흰 — 카드 배경
  sunZone:    "#F2E5C0",   // 감독화면 상단 존

  // 그늘 영역 (휴식, 자연)
  forest:     "#192B1B",   // 짙은 숲 — 감독화면 하단 존
  canopy:     "#3A6630",   // 수관 녹색
  sage:       "#7CAF6E",   // 잎 연녹
  mist:       "#B4D4A8",   // 안개 연녹 (그늘 존 텍스트)

  // 중립
  warmGray:   "#E8DFC8",   // 드라이그라스 — 서피스
  bark:       "#5C4B28",   // 나무껍질 갈색 — 서브 텍스트
  ink:        "#18180E",   // 따뜻한 검정 — 메인 텍스트
  smoke:      "#8A8472",   // 캡션

  // 유틸
  error:      "#B03020",
  white:      "#FFFDF3",
  wave:       "#192B1B",   // 파도 구분선 색 = forest
};

// ── CSS 애니메이션 ────────────────────────────────────────────
const GlobalStyles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #2a2a2a; }

    @keyframes ping {
      0%   { transform: scale(1);   opacity: .55; }
      70%  { transform: scale(1.6); opacity: 0;   }
      100% { transform: scale(1.6); opacity: 0;   }
    }
    @keyframes sunRay {
      0%, 100% { opacity: .12; transform: scale(1);    }
      50%       { opacity: .22; transform: scale(1.06); }
    }
    @keyframes breathe {
      0%, 100% { transform: scale(1);    }
      50%       { transform: scale(1.02); }
    }
    @keyframes slideUp {
      from { transform: translateY(100%); opacity: 0; }
      to   { transform: translateY(0);    opacity: 1; }
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0);   }
    }
    .ping       { animation: ping    1.8s cubic-bezier(0,.2,.8,1) infinite; }
    .sun-ray    { animation: sunRay  3s ease-in-out infinite; }
    .breathe    { animation: breathe 4s ease-in-out infinite; }
    .slide-up   { animation: slideUp .32s cubic-bezier(.22,1,.36,1) both; }
    .fade-in    { animation: fadeIn  .25s ease both; }

    button { font-family: 'Noto Sans KR', sans-serif; }
    input  { font-family: 'Noto Sans KR', sans-serif; }
  `}</style>
);

// ── 신경주역 파일럿 데이터 ────────────────────────────────────
const PLAYGROUNDS = [
  {
    id:"p1", name:"천년가 앞 숲속 공원", distance:"도보 2분",
    status:"active",  members:3, max:6,
    supervisor:"김○○", next:"이○○", min:12, sec:45,
    affiliation:"라라어린이집 학부모", trust:"함께하는 부모",
    roster:[{ch:"김",rest:false},{ch:"이",rest:true},{ch:"박",rest:true}],
    mapX:255, mapY:118,
  },
  {
    id:"p2", name:"건천초 앞 놀이터", distance:"도보 5분",
    status:"open", members:1, max:6,
    affiliation:"해링턴 학부모", trust:"든든한 이웃",
    roster:[{ch:"최",rest:true}],
    mapX:145, mapY:175,
  },
  {
    id:"p3", name:"데시앙 단지 놀이터", distance:"도보 1분",
    status:"empty", members:0, max:6,
    roster:[],
    mapX:280, mapY:200,
  },
];

const AFFILIATIONS = [
  {id:"a1",name:"해링턴플레이스 신경주역",type:"아파트",icon:"🏢",mx:250,my:138},
  {id:"a2",name:"천년가 센텀스카이",      type:"아파트",icon:"🏢",mx:268,my:162},
  {id:"a3",name:"더퍼스트 데시앙",        type:"아파트",icon:"🏢",mx:280,my:195},
  {id:"d1",name:"방주어린이집",           type:"어린이집",icon:"🏫",mx:100,my:82},
  {id:"d2",name:"라라어린이집",           type:"어린이집",icon:"🏫",mx:88, my:106},
  {id:"d3",name:"미래어린이집",           type:"어린이집",icon:"🏫",mx:74, my:132},
];

// ── 지도 SVG 일러스트 (신경주역 권역) ────────────────────────
function IllustratedMap({ onSelect }) {
  const W = 390, H = 290;

  const statusColor = { active:"#C07A22", open:"#3A6630", empty:"#8A8472" };

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`}
      style={{ display:"block", background:"#EDE3C8" }}>

      {/* 배경 지면 */}
      <rect width={W} height={H} fill="#EDE3C8"/>

      {/* 공원 녹지 패치 */}
      {[[220,95,70,60],[62,155,55,45],[155,60,40,30]].map(([x,y,w,h],i)=>(
        <rect key={i} x={x} y={y} width={w} height={h} rx={10}
          fill="#C8DBA8" opacity={.7}/>
      ))}

      {/* 도로망 — 따뜻한 크림 */}
      {/* 수평 주도로 */}
      <rect x={0} y={152} width={W} height={14} fill="#D8CDB0"/>
      {/* 수직 보조도로 */}
      <rect x={186} y={0} width={10} height={H} fill="#D8CDB0"/>
      {/* 보조 수평 */}
      <rect x={0} y={98} width={W} height={7} fill="#DDD3B8" opacity={.7}/>
      <rect x={0} y={198} width={W} height={7} fill="#DDD3B8" opacity={.7}/>
      {/* 보조 수직 */}
      <rect x={130} y={0} width={6} height={H} fill="#DDD3B8" opacity={.7}/>
      <rect x={260} y={0} width={6} height={H} fill="#DDD3B8" opacity={.7}/>

      {/* 건물 블록 */}
      {[[30,30,35,30],[70,30,25,22],[30,66,28,22],[100,30,25,20],
        [310,30,40,28],[320,65,30,22],[310,95,38,24],
        [320,170,40,22],[305,200,35,24]].map(([x,y,w,h],i)=>(
        <rect key={i} x={x} y={y} width={w} height={h} rx={3}
          fill="#D8CEBC" stroke="#C4BAA6" strokeWidth={.8}/>
      ))}

      {/* 신경주역 */}
      <rect x={165} y={144} width={62} height={28} rx={6}
        fill="#192B1B" stroke="#3A6630" strokeWidth={1.5}/>
      <text x={196} y={162} textAnchor="middle"
        fill="#B4D4A8" fontSize={9} fontWeight={700}
        fontFamily="'Noto Sans KR',sans-serif">🚄 신경주역</text>

      {/* 소속 마커 (어린이집·아파트) */}
      {AFFILIATIONS.map(a=>(
        <g key={a.id}>
          <circle cx={a.mx} cy={a.my} r={11}
            fill={a.type==="어린이집"?"#A8C899":"#C8B87A"}
            stroke="#8A7A60" strokeWidth={1} opacity={.85}/>
          <text x={a.mx} y={a.my+4} textAnchor="middle" fontSize={10}>
            {a.icon}
          </text>
        </g>
      ))}

      {/* 놀이터 마커 */}
      {PLAYGROUNDS.map(pg=>(
        <g key={pg.id} style={{cursor:"pointer"}} onClick={()=>onSelect(pg)}>
          {/* 활성 마커 펄스 */}
          {pg.status==="active" && (
            <circle cx={pg.mapX} cy={pg.mapY} r={18}
              fill={statusColor[pg.status]} opacity={.25}
              className="ping"/>
          )}
          {/* 마커 본체 */}
          <circle cx={pg.mapX} cy={pg.mapY} r={13}
            fill={statusColor[pg.status]}
            stroke="#FFFDF3" strokeWidth={2.5}/>
          <text x={pg.mapX} y={pg.mapY+5} textAnchor="middle" fontSize={13}>
            🛝
          </text>
          {/* 인원 뱃지 */}
          {pg.members > 0 && (
            <g>
              <circle cx={pg.mapX+11} cy={pg.mapY-11} r={8}
                fill="#FFFDF3" stroke={statusColor[pg.status]} strokeWidth={1.2}/>
              <text x={pg.mapX+11} y={pg.mapY-8} textAnchor="middle"
                fontSize={7} fontWeight={700} fill={statusColor[pg.status]}
                fontFamily="'Noto Sans KR',sans-serif">{pg.members}</text>
            </g>
          )}
        </g>
      ))}

      {/* 범례 */}
      <rect x={8} y={H-46} width={88} height={40} rx={8}
        fill="rgba(255,253,243,.88)" stroke="#D8CDB0" strokeWidth={1}/>
      {[["#C07A22","진행중"],["#3A6630","모집중"],["#8A8472","빈 곳"]].map(([c,l],i)=>(
        <g key={i}>
          <circle cx={20} cy={H-35+i*11} r={4} fill={c}/>
          <text x={30} y={H-31+i*11} fontSize={8.5} fill="#5C4B28"
            fontFamily="'Noto Sans KR',sans-serif">{l}</text>
        </g>
      ))}
    </svg>
  );
}

// ── 공통: 앰버 버튼 ───────────────────────────────────────────
function AmberBtn({ children, onClick, disabled, size="md", ghost=false }) {
  const pad = size==="lg" ? "18px 0" : "13px 0";
  const fs  = size==="lg" ? 16 : 14;
  return (
    <button onClick={disabled?undefined:onClick} style={{
      width:"100%", padding:pad, borderRadius:14,
      background: disabled ? T.warmGray : ghost ? "transparent" : T.amber,
      color: disabled ? T.smoke : ghost ? T.amber : T.white,
      border: ghost ? `1.5px solid ${T.amber}` : "none",
      fontSize:fs, fontWeight:700, cursor:disabled?"not-allowed":"pointer",
      opacity: disabled ? .7 : 1,
      transition:"all .15s",
      letterSpacing:-.2,
    }}>{children}</button>
  );
}

// ── 공통: 신뢰 뱃지 ──────────────────────────────────────────
function TrustBadge({ level }) {
  const map = {
    "든든한 이웃":    { bg:"#D4EDCF", color:"#1E4D18", dot:"#3A6630" },
    "함께하는 부모":  { bg:"#EDD49A", color:"#5C3D08", dot:"#C07A22" },
    "새내기 부모":    { bg:"#E4DFD3", color:"#5C4B28", dot:"#8A8472" },
  };
  const s = map[level] || map["새내기 부모"];
  return (
    <span style={{
      display:"inline-flex", alignItems:"center", gap:5,
      padding:"3px 10px 3px 8px", borderRadius:99,
      background:s.bg, color:s.color, fontSize:11, fontWeight:700,
    }}>
      <span style={{width:6,height:6,borderRadius:"50%",background:s.dot,flexShrink:0}}/>
      {level}
    </span>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 화면 1: 홈 — 지도
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function HomeScreen({ onSelect }) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%",
      background:T.parchment, fontFamily:"'Noto Sans KR',sans-serif" }}>

      {/* 워드마크 헤더 */}
      <header style={{
        display:"flex", justifyContent:"space-between", alignItems:"center",
        padding:"14px 20px",
        background:"rgba(246,239,216,.92)", backdropFilter:"blur(8px)",
        borderBottom:`1px solid ${T.warmGray}`,
        position:"relative", zIndex:10,
      }}>
        <button style={{background:"none",border:"none",cursor:"pointer",
          color:T.bark, fontSize:16}}>
          🔍
        </button>
        <span style={{ fontSize:20, fontWeight:900, color:T.forest,
          letterSpacing:-1 }}>
          한명만
        </span>
        <button style={{background:"none",border:"none",cursor:"pointer",
          fontSize:16,color:T.bark}}>
          👤
        </button>
      </header>

      {/* 지도 */}
      <div style={{ flex:1, position:"relative", overflow:"hidden" }}>
        <IllustratedMap onSelect={pg=>{onSelect(pg);setDrawerOpen(false);}}/>

        {/* 플로팅 놀이터 카운트 칩 */}
        <div style={{
          position:"absolute", top:10, right:10,
          background:"rgba(25,43,27,.82)", color:T.mist,
          padding:"5px 12px", borderRadius:99,
          fontSize:11, fontWeight:700, backdropFilter:"blur(4px)",
        }}>
          🛝 3곳
        </div>
      </div>

      {/* 하단 드로어 */}
      <div style={{
        background:T.white, borderTop:`1px solid ${T.warmGray}`,
        transition:"max-height .3s ease",
      }}>
        {/* 핸들 */}
        <div onClick={()=>setDrawerOpen(o=>!o)}
          style={{ display:"flex", flexDirection:"column", alignItems:"center",
            padding:"10px 0 8px", cursor:"pointer" }}>
          <div style={{ width:36, height:3, borderRadius:99,
            background:T.warmGray, marginBottom:8 }}/>
          <span style={{ fontSize:12, fontWeight:700, color:T.bark }}>
            {drawerOpen ? "지도 보기 ▼" : "근처 놀이터 ▲"}
          </span>
        </div>

        {/* 카드 리스트 */}
        {!drawerOpen ? (
          /* 미니 스크롤 가로 리스트 */
          <div style={{ display:"flex", gap:10, overflowX:"auto",
            padding:"0 16px 14px", scrollbarWidth:"none" }}>
            {PLAYGROUNDS.map(pg=>(
              <MiniCard key={pg.id} pg={pg} onClick={()=>onSelect(pg)}/>
            ))}
          </div>
        ) : (
          <div style={{ padding:"0 16px 16px", display:"flex",
            flexDirection:"column", gap:10 }}>
            {PLAYGROUNDS.map(pg=>(
              <ExpandedCard key={pg.id} pg={pg} onClick={()=>onSelect(pg)}/>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MiniCard({ pg, onClick }) {
  const col = { active:T.amber, open:T.canopy, empty:T.smoke };
  const lbl = { active:"진행중", open:"모집중", empty:"비어있음" };
  return (
    <button onClick={onClick} style={{
      minWidth:150, background:T.white, border:`1.5px solid ${T.warmGray}`,
      borderRadius:16, padding:"12px 14px", cursor:"pointer",
      textAlign:"left", flexShrink:0, transition:"border-color .15s",
    }}
      onMouseEnter={e=>e.currentTarget.style.borderColor=T.amber}
      onMouseLeave={e=>e.currentTarget.style.borderColor=T.warmGray}
    >
      <div style={{ fontSize:13, fontWeight:700, color:T.ink, marginBottom:5,
        whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis",
        maxWidth:120 }}>{pg.name}</div>
      <div style={{ display:"flex", alignItems:"center", gap:5, marginBottom:4 }}>
        <span style={{ width:6, height:6, borderRadius:"50%",
          background:col[pg.status], flexShrink:0 }}/>
        <span style={{ fontSize:11, color:col[pg.status], fontWeight:600 }}>
          {lbl[pg.status]}
        </span>
      </div>
      <div style={{ fontSize:11, color:T.smoke }}>
        👥 {pg.members}/{pg.max} · {pg.distance}
      </div>
    </button>
  );
}

function ExpandedCard({ pg, onClick }) {
  const col = { active:T.amber, open:T.canopy, empty:T.smoke };
  const lbl = { active:"감독 진행중", open:"모집 중", empty:"비어있음" };
  return (
    <button onClick={onClick} style={{
      width:"100%", background:T.white, border:`1.5px solid ${T.warmGray}`,
      borderRadius:18, padding:"16px 18px", cursor:"pointer", textAlign:"left",
      display:"flex", justifyContent:"space-between", alignItems:"center",
    }}>
      <div>
        <div style={{ fontSize:15, fontWeight:700, color:T.ink,
          marginBottom:4 }}>{pg.name}</div>
        <div style={{ fontSize:11, color:T.smoke }}>{pg.distance}</div>
      </div>
      <div style={{ display:"flex", flexDirection:"column", alignItems:"flex-end",
        gap:4 }}>
        <span style={{ fontSize:11, fontWeight:700, color:col[pg.status],
          background:col[pg.status]+"18", padding:"3px 9px", borderRadius:99 }}>
          {lbl[pg.status]}
        </span>
        <span style={{ fontSize:11, color:T.smoke }}>
          👥 {pg.members}/{pg.max}명
        </span>
      </div>
    </button>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 화면 2: 놀이터 상세 시트
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function PlaygroundSheet({ pg, onJoin, onBack }) {
  const isActive = pg.status === "active";
  const isEmpty  = pg.status === "empty";

  return (
    <div className="fade-in" style={{ display:"flex", flexDirection:"column",
      height:"100%", background:T.parchment,
      fontFamily:"'Noto Sans KR',sans-serif" }}>

      {/* 미니 지도 */}
      <div style={{ height:"28%", position:"relative", overflow:"hidden" }}>
        <IllustratedMap onSelect={()=>{}}/>
        <div style={{ position:"absolute", inset:0,
          background:"rgba(25,43,27,.18)" }}/>
        <button onClick={onBack} style={{
          position:"absolute", top:12, left:14,
          background:"rgba(255,253,243,.9)", border:"none", borderRadius:20,
          padding:"6px 13px", cursor:"pointer", fontSize:12, fontWeight:700,
          color:T.forest, display:"flex", alignItems:"center", gap:5,
        }}>← 지도</button>

        {/* 긴급 버튼 (항상 노출) */}
        <button style={{
          position:"absolute", bottom:14, right:14,
          width:48, height:48, borderRadius:"50%",
          background:T.error, color:"#fff",
          border:"none", cursor:"pointer", fontSize:20,
          boxShadow:`0 4px 16px rgba(176,48,32,.45)`,
          display:"flex", alignItems:"center", justifyContent:"center",
        }}>🚨</button>
      </div>

      {/* 바텀 시트 */}
      <div className="slide-up" style={{
        flex:1, background:T.white, borderRadius:"22px 22px 0 0",
        marginTop:-18, position:"relative", zIndex:5, overflowY:"auto",
        paddingBottom:24,
      }}>
        <div style={{ width:36, height:3, borderRadius:99,
          background:T.warmGray, margin:"10px auto 18px" }}/>

        <div style={{ padding:"0 22px" }}>
          {/* 헤더 */}
          <div style={{ display:"flex", justifyContent:"space-between",
            alignItems:"flex-start", marginBottom:10 }}>
            <h2 style={{ fontSize:22, fontWeight:900, color:T.ink,
              letterSpacing:-.5, lineHeight:1.2, maxWidth:"70%" }}>
              {pg.name}
            </h2>
            <span style={{ fontSize:12, color:T.amber, fontWeight:600,
              marginTop:4 }}>📍 {pg.distance}</span>
          </div>

          {/* 뱃지 */}
          <div style={{ display:"flex", gap:6, flexWrap:"wrap", marginBottom:18 }}>
            {pg.trust && <TrustBadge level={pg.trust}/>}
            {pg.affiliation && (
              <span style={{ fontSize:11, color:T.bark, background:T.warmGray,
                padding:"3px 10px", borderRadius:99 }}>🏷 {pg.affiliation}</span>
            )}
          </div>

          {/* 활성: 미니 썬/쉐이드 카드 */}
          {isActive && (
            <div style={{ borderRadius:18, overflow:"hidden", marginBottom:18,
              border:`1.5px solid ${T.warmGray}` }}>
              {/* 햇볕 영역 */}
              <div style={{ background:`linear-gradient(135deg,${T.amberPale},${T.amberGlow})`,
                padding:"16px 18px" }}>
                <div style={{ fontSize:11, color:T.bark, fontWeight:600,
                  marginBottom:4 }}>지금 감독 중 ☀️</div>
                <div style={{ display:"flex", alignItems:"baseline", gap:8 }}>
                  <span style={{ fontSize:28, fontWeight:900, color:T.ink,
                    fontVariantNumeric:"tabular-nums", letterSpacing:-1 }}>
                    {pg.min}:{String(pg.sec).padStart(2,"0")}
                  </span>
                  <span style={{ fontSize:12, color:T.bark }}>{pg.supervisor}</span>
                </div>
              </div>
              {/* 그늘 영역 */}
              <div style={{ background:T.forest, padding:"12px 18px",
                display:"flex", alignItems:"center", gap:8 }}>
                <span style={{ fontSize:11, color:T.mist, fontWeight:600 }}>
                  다음 🌿
                </span>
                <span style={{ fontSize:13, color:T.mist, fontWeight:700 }}>
                  {pg.next}
                </span>
                <div style={{ marginLeft:"auto", display:"flex", gap:6 }}>
                  {pg.roster.filter(r=>r.rest).map((r,i)=>(
                    <div key={i} style={{
                      width:28, height:28, borderRadius:"50%",
                      background:"rgba(180,212,168,.18)",
                      border:`1px solid ${T.sage}44`,
                      display:"flex", alignItems:"center", justifyContent:"center",
                      fontSize:12, color:T.mist, fontWeight:700,
                    }}>{r.ch}</div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 비어있음 */}
          {isEmpty && (
            <div style={{ background:T.warmGray, borderRadius:18,
              padding:"22px 18px", marginBottom:18, textAlign:"center" }}>
              <div style={{ fontSize:32, marginBottom:8 }}>🌤</div>
              <div style={{ fontSize:14, fontWeight:700, color:T.ink,
                marginBottom:4 }}>아직 아무도 없어요</div>
              <div style={{ fontSize:12, color:T.smoke }}>
                첫 번째로 시작해볼까요?
              </div>
            </div>
          )}

          {/* 참여자 */}
          {pg.roster.length > 0 && (
            <div style={{ marginBottom:20 }}>
              <div style={{ fontSize:11, color:T.smoke, fontWeight:600,
                marginBottom:10 }}>참여 중 · {pg.roster.length}명</div>
              <div style={{ display:"flex", gap:8 }}>
                {pg.roster.map((r,i)=>(
                  <div key={i} style={{
                    width:42, height:42, borderRadius:"50%",
                    background: r.rest ? T.warmGray : T.amber,
                    color: r.rest ? T.bark : T.white,
                    display:"flex", alignItems:"center", justifyContent:"center",
                    fontSize:15, fontWeight:800,
                    border:`2px solid ${r.rest?T.dryGrass:T.amberGlow}`,
                  }}>{r.ch}</div>
                ))}
              </div>
            </div>
          )}

          {/* CTA */}
          <div style={{ display:"flex", gap:10 }}>
            <AmberBtn size="lg" onClick={onJoin}>
              {isEmpty ? "여기서 시작하기" : "참여하기"}
            </AmberBtn>
            {!isEmpty && (
              <button style={{
                padding:"18px 16px", borderRadius:14,
                background:T.warmGray, color:T.smoke,
                border:"none", cursor:"pointer", fontSize:12, fontWeight:600,
                flexShrink:0,
              }}>구경만</button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 화면 3: 감독 운영 — 한낮의 그늘 (서명 화면)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function SupervisionScreen({ pg, onEnd }) {
  const TOTAL = 15 * 60;
  const [secs, setSecs] = useState(pg ? pg.min*60+pg.sec : 12*60+45);
  const [myTurn, setMyTurn] = useState(false); // false = 쉬는 중

  useEffect(()=>{
    const id = setInterval(()=>setSecs(s=>s>0?s-1:0), 1000);
    return ()=>clearInterval(id);
  },[]);

  const m = Math.floor(secs/60);
  const s = secs%60;
  const progress = secs/TOTAL; // 1→0

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%",
      fontFamily:"'Noto Sans KR',sans-serif", position:"relative",
      overflow:"hidden" }}>

      {/* ── 햇볕 존 (상단 58%) ── */}
      <div className="breathe" style={{
        flex:"0 0 58%", position:"relative", overflow:"hidden",
        background:`linear-gradient(160deg, ${T.amberPale} 0%, ${T.amberGlow} 100%)`,
        display:"flex", flexDirection:"column",
        alignItems:"center", justifyContent:"center",
        padding:"0 24px 24px",
      }}>
        {/* 햇살 방사 효과 (SVG) */}
        <svg className="sun-ray" style={{ position:"absolute", inset:0,
          width:"100%", height:"100%", pointerEvents:"none" }}>
          {[0,30,60,90,120,150,180,210,240,270,300,330].map((deg,i)=>(
            <line key={i}
              x1="50%" y1="50%"
              x2={`${50+50*Math.cos((deg-90)*Math.PI/180)}%`}
              y2={`${50+80*Math.sin((deg-90)*Math.PI/180)}%`}
              stroke={T.amber} strokeWidth={1.5} opacity={.15}
              strokeLinecap="round"
            />
          ))}
        </svg>

        {/* 워드마크 + 종료 */}
        <div style={{ position:"absolute", top:0, left:0, right:0,
          display:"flex", justifyContent:"space-between", alignItems:"center",
          padding:"14px 20px" }}>
          <span style={{ fontSize:18, fontWeight:900, color:T.forest,
            letterSpacing:-1 }}>한명만</span>
          <button onClick={onEnd} style={{
            background:`rgba(25,43,27,.12)`, border:"none", borderRadius:20,
            padding:"5px 13px", cursor:"pointer", fontSize:12,
            fontWeight:700, color:T.forest,
          }}>종료</button>
        </div>

        {/* 상태 칩 */}
        <button onClick={()=>setMyTurn(v=>!v)} style={{
          display:"inline-flex", alignItems:"center", gap:6,
          padding:"7px 18px", borderRadius:99, marginBottom:16,
          background: myTurn ? T.amber : T.forest,
          color: myTurn ? T.white : T.mist,
          border:"none", cursor:"pointer", fontSize:13, fontWeight:700,
          boxShadow:`0 2px 12px rgba(192,122,34,.3)`,
          transition:"all .25s",
        }}>
          {myTurn ? "☀️ 지금 감독 중" : "🌿 지금 쉬는 중"}
        </button>

        {/* 슈퍼바이저 아바타 */}
        {myTurn && (
          <div className="breathe" style={{
            width:60, height:60, borderRadius:"50%",
            background:T.amber, color:T.white,
            display:"flex", alignItems:"center", justifyContent:"center",
            fontSize:22, fontWeight:900, marginBottom:12,
            boxShadow:`0 0 0 6px ${T.amberGlow}88`,
          }}>나</div>
        )}

        {/* 타이머 — 이 앱의 심장 */}
        <div style={{ textAlign:"center", marginBottom:10 }}>
          <div style={{
            fontSize:82, fontWeight:900, color:T.ink,
            letterSpacing:-5, lineHeight:1,
            fontVariantNumeric:"tabular-nums",
            textShadow:`0 2px 24px rgba(192,122,34,.18)`,
          }}>
            {String(m).padStart(2,"0")}
            <span style={{ color:T.amber, fontSize:60, margin:"0 -4px" }}>:</span>
            {String(s).padStart(2,"0")}
          </div>
          <div style={{ fontSize:11, color:T.bark, fontWeight:600,
            marginTop:4, letterSpacing:.5 }}>남은 시간</div>
        </div>

        {/* 얇은 프로그레스 바 */}
        <div style={{ width:"70%", height:3, background:T.amberGlow+"88",
          borderRadius:99, overflow:"hidden" }}>
          <div style={{
            width:`${progress*100}%`, height:"100%",
            background:T.amber, borderRadius:99,
            transition:"width 1s linear",
          }}/>
        </div>

        {/* 유기적 파도 구분선 */}
        <svg viewBox="0 0 390 36" style={{
          position:"absolute", bottom:-1, left:0, width:"100%",
          display:"block", lineHeight:0,
        }} preserveAspectRatio="none">
          <path d="M0,14 C65,28 130,2 195,16 C260,30 325,4 390,18 L390,36 L0,36 Z"
            fill={T.forest}/>
        </svg>
      </div>

      {/* ── 그늘 존 (하단 42%) ── */}
      <div style={{
        flex:"0 0 42%", background:T.forest,
        display:"flex", flexDirection:"column",
        padding:"22px 24px 0",
        position:"relative",
      }}>
        <div style={{ fontSize:11, color:T.sage, fontWeight:700,
          letterSpacing:.8, marginBottom:16 }}>🌿 쉬는 중</div>

        {/* 쉬는 부모 카드들 */}
        <div style={{ display:"flex", flexDirection:"column", gap:10,
          overflowY:"auto" }}>
          {[
            { ch:"이", name:"이○○", isNext:true },
            { ch:"박", name:"박○○", isNext:false },
          ].map((r,i)=>(
            <div key={i} style={{
              display:"flex", justifyContent:"space-between",
              alignItems:"center",
              padding:"12px 16px", borderRadius:14,
              background:"rgba(255,253,243,.06)",
              border:`1px solid rgba(180,212,168,${r.isNext?.22:.1})`,
            }}>
              <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                <div style={{
                  width:38, height:38, borderRadius:"50%",
                  background:"rgba(180,212,168,.15)",
                  border:`1.5px solid ${T.sage}44`,
                  display:"flex", alignItems:"center", justifyContent:"center",
                  fontSize:15, color:T.mist, fontWeight:800,
                }}>{r.ch}</div>
                <span style={{ fontSize:14, color:T.mist, fontWeight:500 }}>
                  {r.name}
                </span>
              </div>
              {r.isNext && (
                <span style={{
                  fontSize:11, color:T.canopy, fontWeight:700,
                  background:"rgba(58,102,48,.35)",
                  padding:"3px 10px", borderRadius:99,
                }}>다음 ↑</span>
              )}
            </div>
          ))}
        </div>

        {/* 긴급 버튼 */}
        <button style={{
          position:"absolute", bottom:20, right:20,
          width:54, height:54, borderRadius:"50%",
          background:T.error, color:"#fff",
          border:`2px solid rgba(255,255,255,.2)`,
          cursor:"pointer", fontSize:22,
          boxShadow:`0 4px 20px rgba(176,48,32,.5)`,
          display:"flex", alignItems:"center", justifyContent:"center",
        }}>🚨</button>
      </div>
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 화면 4: 그룹 생성
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function CreateScreen({ pg, onComplete, onBack }) {
  const [step, setStep]     = useState(1);
  const [agreed, setAgreed] = useState(false);
  const target = pg || PLAYGROUNDS[2];

  const steps = ["놀이터", "소속", "동의", "완료"];

  return (
    <div className="fade-in" style={{ display:"flex", flexDirection:"column",
      height:"100%", background:T.parchment,
      fontFamily:"'Noto Sans KR',sans-serif" }}>

      {/* 헤더 */}
      <header style={{ padding:"14px 20px",
        display:"flex", alignItems:"center", gap:14,
        borderBottom:`1px solid ${T.warmGray}` }}>
        <button onClick={step>1?()=>setStep(s=>s-1):onBack} style={{
          background:"none", border:"none", cursor:"pointer",
          fontSize:18, color:T.bark }}>←</button>
        <div style={{ flex:1 }}>
          <div style={{ fontSize:11, color:T.smoke, fontWeight:600,
            marginBottom:5 }}>
            {step}/{steps.length} — {steps[step-1]}
          </div>
          <div style={{ display:"flex", gap:4 }}>
            {steps.map((_,i)=>(
              <div key={i} style={{
                height:3, flex:1, borderRadius:99,
                background: i<step ? T.amber : T.warmGray,
                transition:"background .3s",
              }}/>
            ))}
          </div>
        </div>
      </header>

      <main style={{ flex:1, padding:"32px 24px",
        display:"flex", flexDirection:"column", justifyContent:"space-between" }}>

        <div className="fade-in">
          {step===1 && (
            <>
              <div style={{ fontSize:44, marginBottom:12 }}>📍</div>
              <h2 style={{ fontSize:24, fontWeight:900, color:T.ink,
                letterSpacing:-.5, marginBottom:6 }}>여기서 시작해요</h2>
              <p style={{ fontSize:13, color:T.smoke, marginBottom:24 }}>
                선택한 놀이터를 확인해주세요
              </p>
              <div style={{ background:T.white, border:`2px solid ${T.amber}`,
                borderRadius:18, padding:20 }}>
                <div style={{ fontSize:18, fontWeight:700, color:T.ink,
                  marginBottom:4 }}>{target.name}</div>
                <div style={{ fontSize:12, color:T.smoke }}>
                  📍 {target.distance || "경주 건천읍"}
                </div>
              </div>
            </>
          )}
          {step===2 && (
            <>
              <div style={{ fontSize:44, marginBottom:12 }}>🏷</div>
              <h2 style={{ fontSize:24, fontWeight:900, color:T.ink,
                letterSpacing:-.5, marginBottom:6 }}>소속 확인</h2>
              <p style={{ fontSize:13, color:T.smoke, marginBottom:24 }}>
                같은 소속 학부모에게만 공개됩니다
              </p>
              <div style={{ background:T.white, border:`1px solid ${T.warmGray}`,
                borderRadius:18, padding:20 }}>
                <div style={{ fontSize:11, color:T.smoke, marginBottom:4 }}>
                  내 소속
                </div>
                <div style={{ fontSize:17, fontWeight:700, color:T.ink,
                  marginBottom:8 }}>라라어린이집 학부모</div>
                <TrustBadge level="함께하는 부모"/>
              </div>
            </>
          )}
          {step===3 && (
            <>
              <div style={{ fontSize:44, marginBottom:12 }}>📋</div>
              <h2 style={{ fontSize:24, fontWeight:900, color:T.ink,
                letterSpacing:-.5, marginBottom:6 }}>마지막 확인</h2>
              <p style={{ fontSize:13, color:T.smoke, marginBottom:24 }}>
                시작하기 전에 꼭 읽어주세요
              </p>
              <div style={{ background:T.white, borderRadius:18,
                padding:"18px 20px", marginBottom:20,
                border:`1px solid ${T.warmGray}` }}>
                {[
                  "아이 감독 책임은 각 부모 본인에게 있습니다",
                  "앱은 순번 안내 도구이며 보육을 대행하지 않습니다",
                  "사고 발생 시 해당 시점 감독자가 1차 책임자입니다",
                ].map((t,i)=>(
                  <div key={i} style={{ display:"flex", alignItems:"flex-start",
                    gap:10, marginBottom:i<2?12:0 }}>
                    <span style={{ color:T.canopy, fontWeight:700,
                      fontSize:14, flexShrink:0, marginTop:1 }}>✓</span>
                    <span style={{ fontSize:13, color:T.ink, lineHeight:1.55 }}>
                      {t}
                    </span>
                  </div>
                ))}
              </div>
              <label style={{ display:"flex", alignItems:"center", gap:12,
                cursor:"pointer" }}>
                <input type="checkbox" checked={agreed}
                  onChange={e=>setAgreed(e.target.checked)}
                  style={{ width:20, height:20, accentColor:T.amber }}/>
                <span style={{ fontSize:14, fontWeight:600, color:T.ink }}>
                  위 내용을 확인했습니다
                </span>
              </label>
            </>
          )}
          {step===4 && (
            <div style={{ textAlign:"center", padding:"20px 0" }}>
              <div style={{ fontSize:64, marginBottom:16 }}>🎉</div>
              <div style={{ fontSize:22, fontWeight:900, color:T.ink,
                marginBottom:8 }}>그룹이 만들어졌어요!</div>
              <div style={{ fontSize:13, color:T.smoke, lineHeight:1.6 }}>
                이제 같은 소속 학부모들에게<br/>
                그룹이 공개됩니다
              </div>
            </div>
          )}
        </div>

        <div style={{ marginTop:24 }}>
          {step<4 ? (
            <AmberBtn size="lg"
              disabled={step===3 && !agreed}
              onClick={()=>setStep(s=>s+1)}>
              {step===3 ? "동의하고 시작하기" : "다음"}
            </AmberBtn>
          ) : (
            <AmberBtn size="lg" onClick={onComplete}>
              감독 화면으로 →
            </AmberBtn>
          )}
        </div>
      </main>
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 화면 5: 온보딩
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function OnboardingScreen({ onDone }) {
  const [step, setStep]  = useState(0);
  const [phone, setPhone] = useState("");
  const [picked, setPicked] = useState(null);

  const slides = [
    { icon:"☀️", head:"한명만", sub:"한 명이 감독하는 동안\n나머지 부모는 제대로 쉽니다" },
    { icon:"🌿", head:"번갈아 쉬어요", sub:"자동 순번으로 돌아가며\n감독하고 커피 한 잔 마셔요" },
    { icon:"🛝", head:"우리 동네 놀이터", sub:"같은 어린이집·단지\n학부모끼리만 매칭됩니다" },
  ];

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%",
      background:T.parchment, fontFamily:"'Noto Sans KR',sans-serif" }}>

      {step < 3 ? (
        /* 인트로 슬라이드 */
        <div className="fade-in" style={{ flex:1, display:"flex",
          flexDirection:"column", alignItems:"center",
          justifyContent:"center", padding:"0 32px 32px" }}>
          <div style={{ fontSize:72, marginBottom:28, lineHeight:1 }}>
            {slides[step].icon}
          </div>
          <h1 style={{ fontSize:28, fontWeight:900, color:T.forest,
            marginBottom:12, letterSpacing:-1, textAlign:"center" }}>
            {slides[step].head}
          </h1>
          <p style={{ fontSize:14, color:T.bark, lineHeight:1.7,
            textAlign:"center", whiteSpace:"pre-line", marginBottom:40 }}>
            {slides[step].sub}
          </p>

          {/* 도트 인디케이터 */}
          <div style={{ display:"flex", gap:6, marginBottom:32 }}>
            {slides.map((_,i)=>(
              <div key={i} style={{ width:i===step?20:6, height:6,
                borderRadius:99, background:i===step?T.amber:T.warmGray,
                transition:"all .3s" }}/>
            ))}
          </div>
          <AmberBtn size="lg" onClick={()=>setStep(s=>s+1)}>
            {step<2?"다음 →":"시작하기"}
          </AmberBtn>
        </div>
      ) : step===3 ? (
        /* 전화번호 */
        <div className="fade-in" style={{ flex:1, padding:"48px 28px 28px",
          display:"flex", flexDirection:"column" }}>
          <h2 style={{ fontSize:24, fontWeight:900, color:T.ink,
            marginBottom:6, letterSpacing:-.5 }}>전화번호 인증</h2>
          <p style={{ fontSize:13, color:T.smoke, marginBottom:32 }}>
            본인 인증을 위해 전화번호를 입력해주세요
          </p>
          <input value={phone} onChange={e=>setPhone(e.target.value)}
            placeholder="010-0000-0000" type="tel"
            style={{ padding:"16px 18px", borderRadius:14, fontSize:17,
              background:T.white, border:`1.5px solid ${T.warmGray}`,
              color:T.ink, outline:"none", marginBottom:14,
              fontFamily:"'Noto Sans KR',sans-serif",
              transition:"border-color .2s",
            }}
            onFocus={e=>e.target.style.borderColor=T.amber}
            onBlur={e=>e.target.style.borderColor=T.warmGray}
          />
          <AmberBtn size="lg" onClick={()=>setStep(4)}>
            인증번호 받기
          </AmberBtn>
        </div>
      ) : (
        /* 소속 선택 */
        <div className="fade-in" style={{ flex:1, padding:"32px 22px 28px",
          display:"flex", flexDirection:"column", overflowY:"auto" }}>
          <h2 style={{ fontSize:24, fontWeight:900, color:T.ink,
            marginBottom:6, letterSpacing:-.5 }}>어느 곳에 속해 계신가요?</h2>
          <p style={{ fontSize:13, color:T.smoke, marginBottom:20 }}>
            같은 소속 학부모끼리 그룹이 매칭됩니다
          </p>
          <div style={{ display:"flex", flexDirection:"column", gap:8,
            marginBottom:20, flex:1 }}>
            {AFFILIATIONS.map(a=>(
              <button key={a.id} onClick={()=>setPicked(a.id)} style={{
                padding:"14px 18px", borderRadius:16, cursor:"pointer",
                textAlign:"left", border:`1.5px solid ${picked===a.id?T.amber:T.warmGray}`,
                background: picked===a.id ? T.amberPale : T.white,
                display:"flex", alignItems:"center", gap:14,
                transition:"all .15s",
              }}>
                <span style={{ fontSize:24, flexShrink:0 }}>{a.icon}</span>
                <div>
                  <div style={{ fontSize:14, fontWeight:700, color:T.ink }}>
                    {a.name}
                  </div>
                  <div style={{ fontSize:11, color:T.smoke, marginTop:1 }}>
                    {a.type}
                  </div>
                </div>
                {picked===a.id && (
                  <span style={{ marginLeft:"auto", color:T.amber,
                    fontSize:16, fontWeight:700 }}>✓</span>
                )}
              </button>
            ))}
          </div>
          <AmberBtn size="lg" disabled={!picked} onClick={onDone}>
            시작하기 →
          </AmberBtn>
        </div>
      )}
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 루트 앱
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export default function App() {
  const [screen, setScreen] = useState("onboarding");
  const [pgCtx, setPgCtx]   = useState(null);

  const go = (s, pg=null) => { if(pg) setPgCtx(pg); setScreen(s); };

  return (
    <div style={{
      width: "100%", maxWidth: 390,
      height: "100vh", maxHeight: 844,
      margin: "0 auto", position: "relative", overflow: "hidden",
      borderRadius: 32,
      boxShadow: "0 24px 64px rgba(0,0,0,.35), 0 0 0 1px rgba(255,255,255,.06)",
      fontFamily: "'Noto Sans KR', sans-serif",
      background: T.parchment,
    }}>
      <GlobalStyles/>

      {screen==="onboarding" && (
        <OnboardingScreen onDone={()=>go("home")}/>
      )}
      {screen==="home" && (
        <HomeScreen onSelect={pg=>go("sheet",pg)}/>
      )}
      {screen==="sheet" && pgCtx && (
        <PlaygroundSheet pg={pgCtx}
          onJoin={()=>go(pgCtx.status==="empty"?"create":"supervision")}
          onBack={()=>go("home")}/>
      )}
      {screen==="supervision" && (
        <SupervisionScreen pg={pgCtx} onEnd={()=>go("home")}/>
      )}
      {screen==="create" && (
        <CreateScreen pg={pgCtx}
          onComplete={()=>go("supervision")}
          onBack={()=>go("sheet")}/>
      )}

      {/* 데모 네비게이션 필 */}
      <div style={{
        position:"fixed", bottom:18, left:"50%",
        transform:"translateX(-50%)",
        background:"rgba(25,43,27,.88)", borderRadius:99,
        padding:"6px 10px", display:"flex", gap:4,
        backdropFilter:"blur(10px)", zIndex:9999,
        boxShadow:"0 4px 20px rgba(0,0,0,.3)",
      }}>
        {[
          ["🌤","온보딩","onboarding"],
          ["🗺","지도","home"],
          ["☀️","감독","supervision"],
        ].map(([em,lb,sc])=>(
          <button key={sc} onClick={()=>go(sc)} style={{
            padding:"5px 11px", borderRadius:99, border:"none",
            cursor:"pointer", fontSize:11, fontWeight:700,
            background: screen===sc ? T.amber : "transparent",
            color: screen===sc ? T.white : "rgba(180,212,168,.75)",
            display:"flex", alignItems:"center", gap:4,
            transition:"all .2s",
          }}>{em} {lb}</button>
        ))}
      </div>
    </div>
  );
}
