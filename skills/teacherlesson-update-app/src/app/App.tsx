import { useState } from 'react';
import svgPaths from "../imports/svg-yp9ddzalpq";

// 과목 정의
const subjects = [
  { id: 'korean', name: '국어', icon: '📚', color: '#FF6B6B' },
  { id: 'math', name: '수학', icon: '🔢', color: '#4ECDC4' },
  { id: 'science', name: '과학', icon: '🔬', color: '#95E1D3' },
  { id: 'social', name: '사회', icon: '🌍', color: '#FFB84D' },
  { id: 'english', name: '영어', icon: '🗣️', color: '#A78BFA' },
  { id: 'art', name: '미술', icon: '🎨', color: '#FB923C' },
  { id: 'music', name: '음악', icon: '🎵', color: '#F472B6' },
  { id: 'pe', name: '체육', icon: '⚽', color: '#34D399' }
];

// 수업 일정 데이터
const scheduleData = [
  {
    date: '2026-04-02',
    lessons: [
      { subject: 'korean', unit: '2단원', topic: '마음을 전하는 글쓰기', time: '09:00-09:40', pdfPath: '국어_2단원_3차시_지도서.pdf' },
      { subject: 'math', unit: '3단원', topic: '곱셈구구 익히기 (5단, 6단)', time: '10:00-10:40', pdfPath: '수학_3단원_5차시_지도서.pdf' },
      { subject: 'science', unit: '4단원', topic: '곤충의 한살이 관찰', time: '11:00-11:40', pdfPath: '과학_4단원_2차시_지도서.pdf' },
      { subject: 'social', unit: '1단원', topic: '우리 고장의 위치 알아보기', time: '13:00-13:40', pdfPath: '사회_1단원_1차시_지도서.pdf' }
    ]
  },
  {
    date: '2026-04-03',
    lessons: [
      { subject: 'math', unit: '3단원', topic: '곱셈구구 익히기 (7단, 8단)', time: '09:00-09:40', pdfPath: '수학_3단원_6차시_지도서.pdf' },
      { subject: 'korean', unit: '2단원', topic: '일기 쓰기 연습', time: '10:00-10:40', pdfPath: '국어_2단원_4차시_지도서.pdf' },
      { subject: 'music', unit: '1단원', topic: '음표와 박자 배우기', time: '11:00-11:40', pdfPath: '음악_1단원_2차시_지도서.pdf' },
      { subject: 'english', unit: '2단원', topic: 'Colors and Shapes', time: '13:00-13:40', pdfPath: '영어_2단원_3차시_지도서.pdf' }
    ]
  },
  {
    date: '2026-04-04',
    lessons: [
      { subject: 'science', unit: '4단원', topic: '개구리의 한살이', time: '09:00-09:40', pdfPath: '과학_4단원_3차시_지도서.pdf' },
      { subject: 'social', unit: '1단원', topic: '고장의 자연환경', time: '10:00-10:40', pdfPath: '사회_1단원_2차시_지도서.pdf' },
      { subject: 'art', unit: '2단원', topic: '수채화 그리기', time: '11:00-11:40', pdfPath: '미술_2단원_1차시_지도서.pdf' },
      { subject: 'pe', unit: '1단원', topic: '달리기와 줄넘기', time: '13:00-13:40', pdfPath: '체육_1단원_4차시_지도서.pdf' }
    ]
  },
  {
    date: '2026-04-07',
    lessons: [
      { subject: 'korean', unit: '2단원', topic: '감정을 표현하는 문장 만들기', time: '09:00-09:40', pdfPath: '국어_2단원_5차시_지도서.pdf' },
      { subject: 'math', unit: '3단원', topic: '곱셈구구 종합 문제', time: '10:00-10:40', pdfPath: '수학_3단원_7차시_지도서.pdf' },
      { subject: 'science', unit: '4단원', topic: '동물의 한살이 비교하기', time: '11:00-11:40', pdfPath: '과학_4단원_4차시_지도서.pdf' },
      { subject: 'social', unit: '1단원', topic: '고장의 특산물 알아보기', time: '13:00-13:40', pdfPath: '사회_1단원_3차시_지도서.pdf' }
    ]
  },
  {
    date: '2026-04-08',
    lessons: [
      { subject: 'math', unit: '3단원', topic: '곱셈 활용 문제 풀기', time: '09:00-09:40', pdfPath: '수학_3단원_8차시_지도서.pdf' },
      { subject: 'korean', unit: '2단원', topic: '친구에게 편지 쓰기', time: '10:00-10:40', pdfPath: '국어_2단원_6차시_지도서.pdf' },
      { subject: 'english', unit: '2단원', topic: 'Numbers 1-20', time: '11:00-11:40', pdfPath: '영어_2단원_4차시_지도서.pdf' },
      { subject: 'music', unit: '1단원', topic: '리듬 악기 연주하기', time: '13:00-13:40', pdfPath: '음악_1단원_3차시_지도서.pdf' }
    ]
  }
];

function getWeekDates(currentDate: Date) {
  const week = [];
  const day = currentDate.getDay();
  const diff = currentDate.getDate() - day + (day === 0 ? -6 : 1); // 월요일로 조정
  
  for (let i = 0; i < 5; i++) { // 월-금
    const date = new Date(currentDate);
    date.setDate(diff + i);
    week.push(date);
  }
  return week;
}

function formatDate(date: Date) {
  return date.toISOString().split('T')[0];
}

function formatDisplayDate(date: Date) {
  return `${date.getMonth() + 1}월 ${date.getDate()}일`;
}

function getDayName(date: Date) {
  const days = ['일', '월', '화', '수', '목', '금', '토'];
  return days[date.getDay()];
}

export default function App() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<string | null>(formatDate(new Date()));
  const [selectedSubjectFilter, setSelectedSubjectFilter] = useState<string | null>(null);

  const weekDates = getWeekDates(currentDate);
  const selectedSchedule = scheduleData.find(s => s.date === selectedDate);

  const filteredLessons = selectedSchedule?.lessons.filter(lesson => 
    !selectedSubjectFilter || lesson.subject === selectedSubjectFilter
  ) || [];

  const goToPreviousWeek = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() - 7);
    setCurrentDate(newDate);
  };

  const goToNextWeek = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() + 7);
    setCurrentDate(newDate);
  };

  const openPdf = (pdfPath: string) => {
    // 실제 구현에서는 로컬 파일 시스템에서 PDF를 여는 로직
    alert(`${pdfPath} 파일을 엽니다.\n\n실제 환경에서는 로컬에 저장된 PDF 파일이 열립니다.`);
  };

  const getSubjectInfo = (subjectId: string) => {
    return subjects.find(s => s.id === subjectId);
  };

  return (
    <div className="bg-[#f9f9ff] min-h-screen">
      {/* Top Navigation Bar */}
      <div className="bg-white h-[64px] w-full z-[2] border-b border-[#e5e7eb]">
        <div className="flex items-center justify-between h-full px-[32px]">
          <div>
            <h1 className="font-['Manrope',sans-serif] font-bold text-[20px] text-[#191c23]">초등학교 수업 일정</h1>
            <p className="font-['Plus_Jakarta_Sans',sans-serif] text-[13px] text-[#6b7280]">김담임 선생님</p>
          </div>
          
          <div className="flex items-center gap-[16px]">
            <button className="flex items-center gap-[8px] px-[20px] py-[10px] bg-[#f3f4f6] rounded-[8px] hover:bg-[#e5e7eb] transition-colors">
              <svg className="size-[18px]" fill="none" viewBox="0 0 18 18">
                <path d={svgPaths.p8a35e00} fill="#414754" />
              </svg>
              <span className="font-['Plus_Jakarta_Sans',sans-serif] text-[14px] text-[#414754]">검색</span>
            </button>
          </div>
        </div>
      </div>

      <div className="flex">
        {/* Sidebar - 과목 필터 */}
        <div className="w-[260px] bg-white border-r border-[#e5e7eb] min-h-[calc(100vh-64px)] p-[24px]">
          <div className="mb-[24px]">
            <h3 className="font-['Plus_Jakarta_Sans',sans-serif] font-semibold text-[12px] text-[#6b7280] mb-[12px] uppercase tracking-[0.5px]">과목 필터</h3>
            <button
              onClick={() => setSelectedSubjectFilter(null)}
              className={`w-full text-left px-[16px] py-[12px] rounded-[8px] mb-[8px] transition-colors ${
                selectedSubjectFilter === null
                  ? 'bg-[#005bbf] text-white'
                  : 'bg-[#f9fafb] text-[#414754] hover:bg-[#f3f4f6]'
              }`}
            >
              <span className="font-['Plus_Jakarta_Sans',sans-serif] font-medium text-[14px]">전체 과목</span>
            </button>
          </div>

          <div className="space-y-[6px]">
            {subjects.map((subject) => (
              <button
                key={subject.id}
                onClick={() => setSelectedSubjectFilter(subject.id)}
                className={`w-full flex items-center gap-[12px] px-[16px] py-[10px] rounded-[8px] transition-colors ${
                  selectedSubjectFilter === subject.id
                    ? 'bg-[#005bbf] text-white'
                    : 'bg-[#f9fafb] text-[#414754] hover:bg-[#f3f4f6]'
                }`}
              >
                <span className="text-[20px]">{subject.icon}</span>
                <span className="font-['Plus_Jakarta_Sans',sans-serif] font-medium text-[14px]">{subject.name}</span>
              </button>
            ))}
          </div>

          <div className="mt-[32px] pt-[24px] border-t border-[#e5e7eb]">
            <div className="bg-[#f0f9ff] border border-[#bae6fd] rounded-[12px] p-[16px]">
              <div className="flex items-start gap-[8px] mb-[8px]">
                <svg className="size-[16px] mt-[2px] flex-shrink-0" fill="none" viewBox="0 0 20 20">
                  <path d={svgPaths.p13915240} fill="#0284c7" />
                </svg>
                <div>
                  <p className="font-['Plus_Jakarta_Sans',sans-serif] font-semibold text-[#0c4a6e] text-[13px] leading-[18px]">
                    지도서 파일 위치
                  </p>
                  <p className="font-['Plus_Jakarta_Sans',sans-serif] text-[#075985] text-[12px] leading-[16px] mt-[4px]">
                    각 수업의 PDF 버튼을 클릭하면 로컬에 저장된 지도서가 열립니다.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 p-[32px]">
          {/* Week Navigation */}
          <div className="bg-white rounded-[16px] shadow-sm border border-[#e5e7eb] p-[24px] mb-[24px]">
            <div className="flex items-center justify-between mb-[20px]">
              <h2 className="font-['Manrope',sans-serif] font-bold text-[24px] text-[#191c23]">
                {currentDate.getFullYear()}년 {currentDate.getMonth() + 1}월
              </h2>
              <div className="flex items-center gap-[8px]">
                <button 
                  onClick={goToPreviousWeek}
                  className="p-[8px] hover:bg-[#f3f4f6] rounded-[6px] transition-colors"
                >
                  <svg className="size-[20px] rotate-90" fill="none" viewBox="0 0 20 20">
                    <path d="M10 3L17 10L10 17M17 10H3" stroke="#414754" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
                <button 
                  onClick={() => {
                    setCurrentDate(new Date());
                    setSelectedDate(formatDate(new Date()));
                  }}
                  className="px-[16px] py-[6px] bg-[#f3f4f6] hover:bg-[#e5e7eb] rounded-[6px] transition-colors"
                >
                  <span className="font-['Plus_Jakarta_Sans',sans-serif] font-medium text-[13px] text-[#414754]">오늘</span>
                </button>
                <button 
                  onClick={goToNextWeek}
                  className="p-[8px] hover:bg-[#f3f4f6] rounded-[6px] transition-colors"
                >
                  <svg className="size-[20px] -rotate-90" fill="none" viewBox="0 0 20 20">
                    <path d="M10 3L17 10L10 17M17 10H3" stroke="#414754" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-5 gap-[12px]">
              {weekDates.map((date) => {
                const dateStr = formatDate(date);
                const daySchedule = scheduleData.find(s => s.date === dateStr);
                const isSelected = selectedDate === dateStr;
                const isToday = dateStr === formatDate(new Date());

                return (
                  <button
                    key={dateStr}
                    onClick={() => setSelectedDate(dateStr)}
                    className={`p-[16px] rounded-[12px] border-2 transition-all ${
                      isSelected
                        ? 'border-[#005bbf] bg-[#eff6ff] shadow-md'
                        : 'border-[#e5e7eb] bg-white hover:border-[#cbd5e1] hover:shadow-sm'
                    }`}
                  >
                    <div className="text-center mb-[8px]">
                      <div className={`font-['Plus_Jakarta_Sans',sans-serif] text-[12px] mb-[4px] ${
                        isSelected ? 'text-[#005bbf] font-semibold' : 'text-[#6b7280]'
                      }`}>
                        {getDayName(date)}요일
                      </div>
                      <div className={`font-['Manrope',sans-serif] font-bold text-[24px] ${
                        isToday ? 'text-[#005bbf]' : isSelected ? 'text-[#191c23]' : 'text-[#414754]'
                      }`}>
                        {date.getDate()}
                      </div>
                      {isToday && (
                        <div className="mt-[4px] px-[8px] py-[2px] bg-[#005bbf] rounded-full inline-block">
                          <span className="font-['Plus_Jakarta_Sans',sans-serif] text-[10px] text-white font-semibold">오늘</span>
                        </div>
                      )}
                    </div>
                    {daySchedule && (
                      <div className="flex flex-wrap gap-[4px] justify-center">
                        {daySchedule.lessons.slice(0, 4).map((lesson, idx) => {
                          const subjectInfo = getSubjectInfo(lesson.subject);
                          return (
                            <div
                              key={idx}
                              className="size-[8px] rounded-full"
                              style={{ backgroundColor: subjectInfo?.color }}
                              title={subjectInfo?.name}
                            />
                          );
                        })}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Lessons for Selected Date */}
          <div className="bg-white rounded-[16px] shadow-sm border border-[#e5e7eb] p-[32px]">
            <div className="flex items-center justify-between mb-[24px]">
              <div>
                <h3 className="font-['Manrope',sans-serif] font-bold text-[20px] text-[#191c23] mb-[4px]">
                  {selectedDate && formatDisplayDate(new Date(selectedDate))} ({getDayName(new Date(selectedDate!))})
                </h3>
                <p className="font-['Plus_Jakarta_Sans',sans-serif] text-[14px] text-[#6b7280]">
                  {filteredLessons.length}개의 수업이 예정되어 있습니다
                </p>
              </div>
            </div>

            {filteredLessons.length === 0 ? (
              <div className="text-center py-[60px]">
                <svg className="size-[48px] mx-auto mb-[16px] opacity-20" fill="none" viewBox="0 0 20 20">
                  <path d={svgPaths.p2a946800} fill="#414754" />
                </svg>
                <p className="font-['Plus_Jakarta_Sans',sans-serif] text-[16px] text-[#9ca3af]">
                  이 날짜에 예정된 수업이 없습니다
                </p>
              </div>
            ) : (
              <div className="space-y-[16px]">
                {filteredLessons.map((lesson, index) => {
                  const subjectInfo = getSubjectInfo(lesson.subject);
                  return (
                    <div
                      key={index}
                      className="border border-[#e5e7eb] rounded-[12px] p-[20px] hover:border-[#005bbf] hover:shadow-md transition-all group"
                    >
                      <div className="flex items-start gap-[20px]">
                        {/* Time */}
                        <div className="flex-shrink-0 w-[100px]">
                          <div className="font-['Plus_Jakarta_Sans',sans-serif] font-semibold text-[14px] text-[#005bbf]">
                            {lesson.time}
                          </div>
                          <div className="font-['Plus_Jakarta_Sans',sans-serif] text-[12px] text-[#6b7280] mt-[2px]">
                            40분
                          </div>
                        </div>

                        {/* Subject Badge */}
                        <div className="flex-shrink-0">
                          <div 
                            className="flex items-center gap-[8px] px-[12px] py-[8px] rounded-[8px]"
                            style={{ backgroundColor: `${subjectInfo?.color}20` }}
                          >
                            <span className="text-[24px]">{subjectInfo?.icon}</span>
                            <span 
                              className="font-['Plus_Jakarta_Sans',sans-serif] font-bold text-[14px]"
                              style={{ color: subjectInfo?.color }}
                            >
                              {subjectInfo?.name}
                            </span>
                          </div>
                        </div>

                        {/* Lesson Info */}
                        <div className="flex-1 min-w-0">
                          <div className="font-['Plus_Jakarta_Sans',sans-serif] text-[12px] text-[#6b7280] mb-[4px]">
                            {lesson.unit}
                          </div>
                          <div className="font-['Manrope',sans-serif] font-bold text-[16px] text-[#191c23] leading-[22px]">
                            {lesson.topic}
                          </div>
                        </div>

                        {/* PDF Button */}
                        <div className="flex-shrink-0">
                          <button
                            onClick={() => openPdf(lesson.pdfPath)}
                            className="flex items-center gap-[8px] px-[16px] py-[10px] bg-[#005bbf] hover:bg-[#004a99] text-white rounded-[8px] transition-colors group-hover:shadow-lg"
                          >
                            <svg className="size-[18px]" fill="none" viewBox="0 0 20 25">
                              <path d={svgPaths.p1ec38700} fill="white" />
                            </svg>
                            <span className="font-['Plus_Jakarta_Sans',sans-serif] font-semibold text-[14px]">
                              지도서 열기
                            </span>
                          </button>
                        </div>
                      </div>

                      {/* PDF Path */}
                      <div className="mt-[12px] pt-[12px] border-t border-[#f3f4f6]">
                        <div className="flex items-center gap-[8px]">
                          <svg className="size-[14px] opacity-40" fill="none" viewBox="0 0 20 20">
                            <path d={svgPaths.p643d217} fill="#414754" />
                          </svg>
                          <span className="font-['Plus_Jakarta_Sans',sans-serif] text-[13px] text-[#9ca3af]">
                            {lesson.pdfPath}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
