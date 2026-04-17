import { groupByDate } from "@/lib/demoData";

function monthDayName(dayIndex) {
  const names = ["일", "월", "화", "수", "목", "금", "토"];
  return names[dayIndex];
}

export function MonthlyCalendar({ slots, boardDate }) {
  const byDate = groupByDate(slots);
  const monthMatrix = getMonthMatrix(boardDate);
  const today = new Date();
  const todayIso = toLocalDateStr(today);

  return (
    <div className="month-calendar">
      <div className="month-calendar-header">
        <div className="month-calendar-title">
          {formatMonthTitle(boardDate)} 월간 달력
        </div>
        <div className="month-calendar-subtitle">
          선택한 주가 속한 달을 날짜별로 보여 줍니다.
        </div>
      </div>

      <div className="month-calendar-grid month-calendar-weekdays">
        {Array.from({ length: 7 }, (_, idx) => (
          <div key={idx} className="month-calendar-weekday">
            {monthDayName(idx)}
          </div>
        ))}
      </div>

      <div className="month-calendar-grid month-calendar-weeks">
        {monthMatrix.map((week, weekIndex) => (
          <div key={weekIndex} className="month-calendar-row">
            {week.map((cell) => {
              const items = byDate[cell.iso] || [];
              const isToday = cell.iso === todayIso;
              return (
                <div
                  key={cell.iso}
                  className={`month-calendar-day${cell.inMonth ? "" : " out-of-month"}${isToday ? " today" : ""}`}
                >
                  <div className="month-calendar-day-header">
                    <span>{cell.date.getDate()}</span>
                    {items.length > 0 && (
                      <span className="month-calendar-day-count">{items.length}</span>
                    )}
                  </div>
                  <div className="month-calendar-day-items">
                    {items.slice(0, 2).map((item) => (
                      <div key={item.id} className="month-calendar-day-item">
                        {item.subject}
                      </div>
                    ))}
                    {items.length > 2 && (
                      <div className="month-calendar-day-more">+{items.length - 2}개</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function toLocalDateStr(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getMonthMatrix(dateStr) {
  const base = new Date(dateStr + "T00:00:00");
  const year = base.getFullYear();
  const month = base.getMonth();
  const firstOfMonth = new Date(year, month, 1);
  const lastOfMonth = new Date(year, month + 1, 0);
  const startDate = new Date(firstOfMonth);
  startDate.setDate(firstOfMonth.getDate() - firstOfMonth.getDay());
  const endDate = new Date(lastOfMonth);
  endDate.setDate(lastOfMonth.getDate() + (6 - lastOfMonth.getDay()));

  const weeks = [];
  let week = [];
  const cursor = new Date(startDate);

  while (cursor <= endDate) {
    week.push({
      date: new Date(cursor),
      iso: toLocalDateStr(cursor),
      inMonth: cursor.getMonth() === month,
    });

    if (week.length === 7) {
      weeks.push(week);
      week = [];
    }
    cursor.setDate(cursor.getDate() + 1);
  }

  return weeks;
}

function formatMonthTitle(dateStr) {
  const date = new Date(dateStr + "T00:00:00");
  return `${date.getMonth() + 1}월`;
}
