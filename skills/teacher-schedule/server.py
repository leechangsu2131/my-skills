import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import date, timedelta
import schedule

app = Flask(__name__)
CORS(app)

@app.route('/api/dashboard')
def dashboard():
    ws = schedule.connect()
    records = schedule.load_all(ws)
    subjects = schedule.get_subjects(records)
    
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    views = []
    
    today_lessons = schedule.get_schedule_by_date(records, today)
    views.append({"id": "today", "label": "오늘", "title": f"오늘 수업 ({today.strftime('%Y-%m-%d')})", "type": "lesson_list", "data": today_lessons})
    
    tomorrow_lessons = schedule.get_schedule_by_date(records, tomorrow)
    views.append({"id": "tomorrow", "label": "내일", "title": f"내일 수업 ({tomorrow.strftime('%Y-%m-%d')})", "type": "lesson_list", "data": tomorrow_lessons})
    
    next_monday = today + timedelta(days=(7 - today.weekday()))
    nextweek_lessons = []
    for i in range(5):
        d = next_monday + timedelta(days=i)
        nextweek_lessons.extend(schedule.get_schedule_by_date(records, d))
    views.append({"id": "nextweek", "label": "다음 주", "title": "다음 주 전체 수업", "type": "lesson_list", "data": nextweek_lessons})
    
    next_classes = {}
    for sub in subjects:
        all_sub = [r for r in records if r.get("과목", "").strip() == sub]
        done_list = [r for r in all_sub if str(r.get("실행여부", "FALSE")).upper() == "TRUE"]
        recent = done_list[-1] if done_list else None
        
        next_cls = schedule.get_next_class(records, sub)
        if next_cls or recent:
            next_classes[sub] = {"next": next_cls, "recent": recent}
            
    views.append({"id": "next", "label": "다음 차시", "title": "과목별 직전 완료 및 다음 수업", "type": "next_class_grid", "data": next_classes})
    
    progress_data = {sub: schedule.get_progress(records, sub) for sub in subjects}
    views.append({"id": "progress", "label": "진도율", "title": "현재까지 과목별 진도 현황", "type": "progress_list", "data": progress_data})
    
    unit_progress_data = {}
    for sub in subjects:
        all_sub = [r for r in records if r.get("과목", "").strip() == sub]
        units_dict = {}
        for r in all_sub:
            unit_name = r.get("대단원", "").strip()
            if not unit_name:
                unit_name = "기타 차시"
                
            if unit_name not in units_dict:
                units_dict[unit_name] = {"total": 0, "completed": 0, "lessons": []}
                
            units_dict[unit_name]["total"] += 1
            is_done = str(r.get("실행여부", "FALSE")).upper() in ("TRUE", "1", "Y", "YES", "DONE")
            if isinstance(r.get("실행여부"), bool):
                is_done = r.get("실행여부")
                
            if is_done:
                units_dict[unit_name]["completed"] += 1
                
            units_dict[unit_name]["lessons"].append({
                "차시": r.get("차시", ""),
                "수업내용": r.get("수업내용", ""),
                "실행여부": is_done,
                "계획일": r.get("계획일", ""),
                "_row": r.get("_row")
            })
            
        units_list = []
        for name, data in units_dict.items():
            pct = round((data["completed"] / data["total"] * 100)) if data["total"] > 0 else 0
            units_list.append({
                "name": name,
                "total": data["total"],
                "completed": data["completed"],
                "percentage": pct,
                "lessons": data["lessons"]
            })
            
        unit_progress_data[sub] = units_list
        
    views.append({"id": "unit_progress", "label": "단원 추적", "title": "단원별 상세 진도 (Tree View)", "type": "unit_progress", "data": unit_progress_data})
    
    views.append({"id": "push", "label": "일정 연기", "title": "특정 과목 수업 일정 미루기", "type": "push_action", "data": None})
    views.append({"id": "extend", "label": "차시 연장", "title": "진행 중인 차시 분량 늘리기(행 복제)", "type": "extend_action", "data": None})
            
    return jsonify({"views": views, "subjects": subjects})

@app.route('/api/done', methods=['POST'])
def done():
    data = request.json
    subject = data.get('subject')
    target = data.get('target_date')
    target_date = date.fromisoformat(target) if target else None
    ws = schedule.connect()
    records = schedule.load_all(ws)
    schedule.mark_done(ws, records, subject, target_date)
    return jsonify({"status": "success", "message": f"{subject} 완료 처리됨"})

@app.route('/api/push', methods=['POST'])
def push():
    data = request.json
    subject = data.get('subject')
    days = data.get('days', 7)
    target = data.get('from_date')
    from_date = date.fromisoformat(target) if target else None
    ws = schedule.connect()
    records = schedule.load_all(ws)
    schedule.push_schedule(ws, records, subject, days, from_date)
    return jsonify({"status": "success", "message": f"{subject} {days}일 밀기 완료"})

@app.route('/api/extend', methods=['POST'])
def extend():
    data = request.json
    subject = data.get('subject')
    ws = schedule.connect()
    records = schedule.load_all(ws)
    schedule.extend_lesson(ws, records, subject)
    return jsonify({"status": "success", "message": f"{subject} 차시 연장 처리 완료"})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
