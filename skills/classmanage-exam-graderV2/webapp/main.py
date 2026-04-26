"""
classmanage-exam-graderV2  ─  webapp/main.py (리팩토링 버전)
목적: YOLO BBox 라벨 데이터 축적
- AI API 없음
- answers.json / 채점 / OCR 로직 없음
"""
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json, os, sys, logging

# ── 경로 설정 ──────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent.parent
LOG_DIR         = BASE_DIR / "logs"
PDF_DIR         = BASE_DIR / "data" / "raw_pdfs"
RAW_DIR         = BASE_DIR / "data" / "raw_images"
ALIGNED_DIR     = BASE_DIR / "data" / "aligned_images"
TEMPLATE_DIR    = BASE_DIR / "data" / "template"
ANSWERS_DIR     = BASE_DIR / "data" / "answers"
ANNO_DIR        = BASE_DIR / "data" / "json"          # regions.json
YOLO_DIR        = BASE_DIR / "data" / "yolo_labels"

for d in [LOG_DIR, PDF_DIR, RAW_DIR, ALIGNED_DIR, TEMPLATE_DIR,
          ANSWERS_DIR, ANNO_DIR, YOLO_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 마이그레이션: 기존 blank.jpg 가 있으면 blank_p1.jpg 로 이름 변경
old_blank = TEMPLATE_DIR / "blank.jpg"
if old_blank.exists():
    old_blank.rename(TEMPLATE_DIR / "blank_p1.jpg")

# ── 로깅 ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "server.log", encoding="utf-8"),
        logging.StreamHandler(sys.__stdout__),
    ]
)

sys.path.insert(0, str(BASE_DIR / "src"))
import event_logger as _elog
_elog.init(LOG_DIR)
_elog.log_event("app_started")

# ── FastAPI 앱 ────────────────────────────────────────────
app = FastAPI(title="Exam Grader V2")
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# ── 헬퍼 ─────────────────────────────────────────────────
IMG_EXT = {".jpg", ".jpeg", ".png"}

def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _imread_safe(path: str):
    """한글 경로 대응 OpenCV 읽기"""
    import cv2, numpy as np
    arr = np.fromfile(path, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

def _imwrite_safe(path: str, img):
    """한글 경로 대응 OpenCV 쓰기"""
    import cv2
    ext = Path(path).suffix
    ok, buf = cv2.imencode(ext, img)
    if ok:
        with open(path, "wb") as f:
            buf.tofile(f)

# ══════════════════════════════════════════════════════════
# 페이지 라우트
# ══════════════════════════════════════════════════════════

@app.get("/")
async def dashboard(request: Request):
    """메인 대시보드 — AI 브릿지 + 업로드 + 파이프라인"""
    aligned = sorted(p.name for p in ALIGNED_DIR.iterdir()
                     if p.suffix.lower() in IMG_EXT)
    has_regions = (ANNO_DIR / "regions.json").exists()
    templates = sorted(p.name for p in TEMPLATE_DIR.iterdir() if p.suffix.lower() in IMG_EXT and p.name.startswith("blank_"))
    return TEMPLATES.TemplateResponse(request, "index.html", {
        "aligned_images": aligned,
        "has_regions": has_regions,
        "template_exists": len(templates) > 0,
        "templates": templates
    })

@app.get("/review")
async def review_page():
    """오버레이 검수 에디터"""
    return FileResponse(str(STATIC_DIR / "review2.html"), media_type="text/html")

# ══════════════════════════════════════════════════════════
# API — 업로드 / 파이프라인
# ══════════════════════════════════════════════════════════

@app.post("/api/upload/template")
async def upload_template(file: UploadFile = File(...)):
    import shutil, tempfile
    import traceback
    
    try:
        ext = Path(file.filename).suffix.lower()
        TEMPLATE_DIR.mkdir(exist_ok=True)
        
        # 기존 템플릿 파일 삭제
        for p in TEMPLATE_DIR.glob("blank_*.jpg"):
            p.unlink()

        if ext in [".jpg", ".jpeg", ".png"]:
            with open(TEMPLATE_DIR / "blank_p1.jpg", "wb") as f:
                shutil.copyfileobj(file.file, f)
            _elog.log_event("template_uploaded", {"type": "image", "pages": 1})
            return {"success": True, "pages": 1}

        elif ext == ".pdf":
            import fitz
            with tempfile.TemporaryDirectory() as tmp:
                tmp_pdf = Path(tmp) / "t.pdf"
                with open(tmp_pdf, "wb") as f:
                    shutil.copyfileobj(file.file, f)
                doc = fitz.open(str(tmp_pdf))
                pages_count = len(doc)
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72), alpha=False)
                    pix.save(str(TEMPLATE_DIR / f"blank_p{i+1}.jpg"))
                doc.close()
            _elog.log_event("template_uploaded", {"type": "pdf", "pages": pages_count})
            return {"success": True, "pages": pages_count}
            
        return {"success": False, "error": f"지원하지 않는 형식 ({ext})"}
        
    except Exception as e:
        error_msg = str(e)
        _elog.log_event("template_upload_error", {"error": error_msg, "traceback": traceback.format_exc()})
        return {"success": False, "error": f"서버 처리 오류: {error_msg}"}

@app.post("/api/upload/answers")
async def upload_answers(file: UploadFile = File(...)):
    import shutil
    try:
        ANSWERS_DIR.mkdir(exist_ok=True)
        for p in ANSWERS_DIR.glob("*.pdf"):
            p.unlink()
        
        target_path = ANSWERS_DIR / "answer_key.pdf"
        with open(target_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        _elog.log_event("answers_uploaded", {})
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/upload/students")
async def upload_students(files: list[UploadFile] = File(...)):
    import shutil
    import traceback
    saved = []
    
    try:
        for f in files:
            ext = Path(f.filename).suffix.lower()
            if ext == ".pdf":
                out = PDF_DIR / f.filename
                with open(out, "wb") as buf:
                    shutil.copyfileobj(f.file, buf)
                saved.append(out.name)
            elif ext in IMG_EXT:
                out = RAW_DIR / f.filename
                with open(out, "wb") as buf:
                    shutil.copyfileobj(f.file, buf)
                saved.append(out.name)
                
        _elog.log_event("students_uploaded", {"count": len(saved), "files": saved})
        return {"success": True, "saved": saved}
        
    except Exception as e:
        error_msg = str(e)
        _elog.log_event("students_upload_error", {"error": error_msg, "traceback": traceback.format_exc()})
        return {"success": False, "error": f"서버 처리 오류: {error_msg}"}


@app.post("/api/run_pipeline")
async def run_pipeline(request: Request):
    """PDF 분할 + ORB 정렬 일괄 실행"""
    templates = list(TEMPLATE_DIR.glob("blank_*.jpg"))
    if not templates:
        return {"success": False, "error": "기준 시험지를 먼저 업로드하세요."}

    try:
        data = await request.json()
        cycle = int(data.get("cycle", 0))
    except:
        cycle = len(templates)

    from pdf_handler import convert_pdfs_to_images
    from aligner import align_image
    import re

    # RAW_DIR 비우기 (이전 이미지 완전 정리)
    for p in RAW_DIR.glob("*.*"):
        if p.suffix.lower() in IMG_EXT and not p.name.startswith("blank_"):
            p.unlink()
            
    # ALIGNED_DIR 비우기 (이전 보정본 완전 정리)
    for p in ALIGNED_DIR.glob("*.*"):
        if p.suffix.lower() in IMG_EXT and not p.name.startswith("blank_"):
            p.unlink()

    convert_pdfs_to_images(str(PDF_DIR), str(RAW_DIR), dpi=300, cycle=cycle)

    images = [f for f in os.listdir(RAW_DIR)
              if Path(f).suffix.lower() in IMG_EXT and not f.startswith("blank_")]
    if not images:
        return {"success": False, "error": "처리할 학생 이미지가 없습니다."}

    ok, fail = 0, 0
    for name in images:
        # 파일명에서 페이지 번호 추출 (예: _stu001_p1.jpg -> 1, 또는 _page_01.jpg -> 1)
        m = re.search(r'_p(\d+)\.jpg$', name, re.IGNORECASE)
        if not m:
            m = re.search(r'_page_(\d+)', name, re.IGNORECASE)
        page_num = int(m.group(1)) if m else 1
        
        target_template = TEMPLATE_DIR / f"blank_p{page_num}.jpg"
        if not target_template.exists():
            target_template = TEMPLATE_DIR / "blank_p1.jpg" # fallback

        result = align_image(
            str(RAW_DIR / name),
            str(target_template),
            str(ALIGNED_DIR / f"aligned_{name}")
        )
        if result:
            ok += 1
        else:
            fail += 1

    _elog.log_event("pipeline_done", {"ok": ok, "fail": fail})
    return {"success": True, "aligned": ok, "failed": fail}

# ══════════════════════════════════════════════════════════
# API — regions.json (AI 브릿지 핵심)
# ══════════════════════════════════════════════════════════

@app.get("/api/regions")
async def get_regions():
    data = _load_json(ANNO_DIR / "regions.json")
    if data is None:
        raise HTTPException(status_code=404, detail={
            "error": "regions.json 없음",
            "guide": "대시보드에서 Gemini 결과를 붙여넣어 저장하세요."
        })
    _elog.log_event("regions_loaded")
    return data


@app.post("/api/regions")
async def save_regions(request: Request):
    raw = await request.body()
    # JSON 유효성 검증
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON 파싱 오류: {e}"}
    # questions 키가 없으면 래핑
    if "questions" not in data and isinstance(data, list):
        data = {"questions": data}
    (ANNO_DIR / "regions.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _elog.log_event("regions_saved", {"count": len(data.get("questions", []))})
    return {"success": True, "count": len(data.get("questions", []))}

# ══════════════════════════════════════════════════════════
# API — 이미지 서빙
# ══════════════════════════════════════════════════════════

@app.get("/api/templates")
async def list_templates():
    templates = sorted(p.name for p in TEMPLATE_DIR.iterdir()
                       if p.suffix.lower() in IMG_EXT and p.name.startswith("blank_"))
    return {"pages": templates}

@app.get("/api/template/{name}")
async def serve_template(name: str):
    p = TEMPLATE_DIR / name
    if not p.exists() or not p.name.startswith("blank_"):
        raise HTTPException(status_code=404, detail="해당 템플릿 페이지 없음")
    return FileResponse(str(p), media_type="image/jpeg")

@app.get("/api/files/status")
async def files_status():
    import datetime
    templates = sorted([p.name for p in TEMPLATE_DIR.iterdir() if p.suffix.lower() in IMG_EXT and p.name.startswith("blank_")])
    answers = sorted([p.name for p in ANSWERS_DIR.iterdir() if p.suffix.lower() == ".pdf"])
    
    regions_path = ANNO_DIR / "regions.json"
    regions_info = {"exists": False}
    if regions_path.exists():
        try:
            data = json.loads(regions_path.read_text(encoding="utf-8"))
            qs = data.get("questions", [])
            if not isinstance(qs, list):
                qs = data if isinstance(data, list) else []
            pages = sorted(list(set(q.get("page", 1) for q in qs)))
            mtime = datetime.datetime.fromtimestamp(regions_path.stat().st_mtime).isoformat()
            regions_info = {
                "exists": True,
                "question_count": len(qs),
                "pages": pages,
                "created_at": mtime
            }
        except:
            pass
            
    students = sorted([p.name for p in PDF_DIR.iterdir() if p.suffix.lower() == ".pdf"])
    
    return {
        "template": {"files": templates, "count": len(templates)},
        "answers": {"files": answers, "count": len(answers)},
        "regions": regions_info,
        "students": {"files": students, "count": len(students)}
    }

@app.get("/api/thumbnail")
async def get_thumbnail(path: str, size: int = 120):
    from fastapi.responses import Response
    import fitz, cv2, numpy as np
    
    full_path = BASE_DIR / path
    if not full_path.exists():
        raise HTTPException(status_code=404)
        
    ext = full_path.suffix.lower()
    img_data = None
    
    if ext == ".pdf":
        try:
            doc = fitz.open(str(full_path))
            pix = doc.load_page(0).get_pixmap(matrix=fitz.Matrix(150/72, 150/72), alpha=False)
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            if pix.n == 4:
                img_data = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img_data = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            doc.close()
        except Exception:
            raise HTTPException(status_code=500, detail="PDF thumbnail error")
    elif ext in IMG_EXT:
        img_data = _imread_safe(str(full_path))
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
        
    if img_data is not None:
        h, w = img_data.shape[:2]
        new_w = size
        new_h = int(h * (size / w))
        resized = cv2.resize(img_data, (new_w, new_h))
        ok, buf = cv2.imencode(".jpg", resized)
        if ok:
            return Response(content=buf.tobytes(), media_type="image/jpeg")
            
    raise HTTPException(status_code=500, detail="Thumbnail generation failed")


@app.get("/api/students")
async def list_students():
    files = sorted(p.name for p in ALIGNED_DIR.iterdir()
                   if p.suffix.lower() in IMG_EXT)
    return {"students": files}


@app.get("/api/student/{name}")
async def serve_aligned(name: str):
    p = ALIGNED_DIR / name
    if not p.exists():
        raise HTTPException(status_code=404)
    return FileResponse(str(p))


@app.delete("/api/student/{name}")
async def delete_student_page(name: str):
    p_aligned = ALIGNED_DIR / name
    raw_name = name.replace("aligned_", "")
    p_raw = RAW_DIR / raw_name
    
    deleted = False
    if p_aligned.exists():
        p_aligned.unlink()
        deleted = True
    if p_raw.exists():
        p_raw.unlink()
        deleted = True
        
    if deleted:
        _elog.log_event("student_page_deleted", {"file": name})
        return {"success": True}
    raise HTTPException(status_code=404, detail="File not found")


@app.post("/api/student/offset")
async def save_student_offset(request: Request):
    data = await request.json()
    name = data.get("name")
    dx = int(data.get("dx", 0))
    dy = int(data.get("dy", 0))
    
    if dx == 0 and dy == 0:
        return {"success": True}
        
    p = ALIGNED_DIR / name
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    import cv2
    import numpy as np
    from aligner import _imread_safe, _imwrite_safe
    
    img = _imread_safe(str(p))
    if img is None:
        raise HTTPException(status_code=500, detail="Cannot read image")
        
    h, w = img.shape[:2]
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    shifted = cv2.warpAffine(img, M, (w, h), borderValue=(255,255,255))
    _imwrite_safe(str(p), shifted)
    
    _elog.log_event("student_manual_offset", {"file": name, "dx": dx, "dy": dy})
    return {"success": True}

@app.post("/api/student/restore")
async def restore_student_offset(request: Request):
    data = await request.json()
    name = data.get("name")
    
    raw_name = name.replace("aligned_", "")
    p_raw = RAW_DIR / raw_name
    p_aligned = ALIGNED_DIR / name
    
    if not p_raw.exists():
        raise HTTPException(status_code=404, detail="Raw file not found")
        
    from aligner import align_image
    import re
    m = re.search(r'_p(\d+)\.jpg$', raw_name, re.IGNORECASE)
    if not m:
        m = re.search(r'_page_(\d+)', raw_name, re.IGNORECASE)
    page_num = int(m.group(1)) if m else 1
    
    target_template = TEMPLATE_DIR / f"blank_p{page_num}.jpg"
    if not target_template.exists():
        target_template = TEMPLATE_DIR / "blank_p1.jpg"
        
    align_image(str(p_raw), str(target_template), str(p_aligned))
    _elog.log_event("student_restored", {"file": name})
    return {"success": True}


@app.get("/api/student/{name}/raw")
async def serve_raw(name: str):
    """aligned_ 접두어 제거 후 원본 반환"""
    raw_name = name.replace("aligned_", "")
    p = RAW_DIR / raw_name
    if not p.exists():
        raise HTTPException(status_code=404)
    return FileResponse(str(p))

# ══════════════════════════════════════════════════════════
# API — YOLO 저장 / 로그
# ══════════════════════════════════════════════════════════

@app.post("/api/yolo_save")
async def yolo_save(request: Request):
    payload = await request.json()
    name    = payload.get("name", "template")
    qs      = payload.get("questions", [])
    lines   = []
    for q in qs:
        b  = q.get("box", {})
        cx = b["x"] + b["w"] / 2
        cy = b["y"] + b["h"] / 2
        lines.append(f"0 {cx:.6f} {cy:.6f} {b['w']:.6f} {b['h']:.6f}")
    out = YOLO_DIR / f"{Path(name).stem}.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    _elog.log_event("review_confirmed", {"file": name, "boxes": len(lines)})
    return {"success": True, "saved": str(out), "boxes": len(lines)}


@app.post("/api/log")
async def frontend_log(request: Request):
    payload = await request.json()
    _elog.log_event(payload.get("event", "frontend"), payload.get("detail", {}))
    return {"success": True}
