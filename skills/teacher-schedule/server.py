import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import date, timedelta, datetime
import schedule
import json
import fitz
from io import BytesIO

LOG_FILE = "activity_log.json"

def log_action(action, subject, details=""):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "subject": subject,
        "details": details
    }
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            pass
    logs.insert(0, log_entry)
    logs = logs[:50]
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

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
    
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            pass
    views.append({"id": "history", "label": "최근 활동", "title": "실시간 수행 내역", "type": "history_feed", "data": logs})
    
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
                "pdf파일": r.get("pdf파일", ""),
                "시작페이지": r.get("시작페이지", ""),
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
    log_action("수업 완료", subject, f"{target_date.strftime('%Y-%m-%d')} 일정" if target_date else "최근 차시")
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
    log_action("일정 연기", subject, f"{days}일 미룸 (기준: {from_date.strftime('%Y-%m-%d') if from_date else '전체'})")
    return jsonify({"status": "success", "message": f"{subject} {days}일 밀기 완료"})

@app.route('/api/extend', methods=['POST'])
def extend():
    data = request.json
    subject = data.get('subject')
    ws = schedule.connect()
    records = schedule.load_all(ws)
    schedule.extend_lesson(ws, records, subject)
    log_action("차시 연장", subject, "진행 중 차시 분량 증가")
    return jsonify({"status": "success", "message": f"{subject} 차시 연장 처리 완료"})

@app.route('/api/pdf/<int:row_id>')
def serve_pdf_fragment(row_id):
    ws = schedule.connect()
    records = schedule.load_all(ws)
    record = next((r for r in records if r.get("_row") == row_id), None)
    
    if not record:
        return "Row not found", 404
        
    raw_pdf_path = record.get("pdf파일", "").strip()
    pdf_path = os.path.expandvars(os.path.expanduser(raw_pdf_path))
    start_str = record.get("시작페이지", "")
    end_str = record.get("끝페이지", "")
    
    if not pdf_path or not os.path.exists(pdf_path):
        return f"자료가 연결되지 않았거나, 다음 파일 경로를 찾을 수 없습니다: {pdf_path}", 404
        
    try:
        start_page = int(str(start_str).strip())
        end_page = int(str(end_str).strip()) if str(end_str).strip() else start_page
    except ValueError:
        return "PDF 페이지 범위가 잘못되었습니다.", 400
        
    doc = fitz.open(pdf_path)
    sp = max(0, start_page - 1)
    ep = min(len(doc) - 1, end_page - 1)
    if ep < sp:
        sp, ep = ep, sp
        
    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=sp, to_page=ep)
    
    pdf_bytes = new_doc.write()
    new_doc.close()
    doc.close()
    
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f"{record.get('과목', 'lesson')}_{record.get('차시', 'fragment')}.pdf"
    )

if __name__ == '__main__':
    app.run(port=5000, debug=True)
