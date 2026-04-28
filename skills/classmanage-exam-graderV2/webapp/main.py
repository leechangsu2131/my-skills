"""
Local FastAPI app for project-based exam alignment and review.
"""

from pathlib import Path
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import traceback

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).parent.parent
APP_LOG_DIR = BASE_DIR / "logs"
SETTINGS_FILE = BASE_DIR / "settings.json"
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATE_DIR = Path(__file__).parent / "templates"
IMG_EXT = {".jpg", ".jpeg", ".png"}

APP_LOG_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(APP_LOG_DIR / "server.log", encoding="utf-8"),
        logging.StreamHandler(sys.__stdout__),
    ],
)

sys.path.insert(0, str(BASE_DIR / "src"))

from aligner import align_image  # type: ignore
from assessment_bundle import merge_assessment_bundle, normalize_assessment_bundle  # type: ignore
from pdf_handler import convert_pdfs_to_images  # type: ignore
import event_logger as _elog  # type: ignore
from project_store import (  # type: ignore
    create_project,
    get_project_status,
    load_settings,
    project_paths,
    refresh_project_metadata,
    resolve_project_dir,
    save_settings,
    scan_projects,
)
from ocr_engine import OcrEngine  # type: ignore
from submission_store import (  # type: ignore
    build_submission_manifest,
    generate_reference_crops,
    generate_student_crops,
    list_students_from_aligned,
    load_all_submission_results,
    load_submission_result,
    run_ocr_for_project,
    score_project_submissions,
    write_submission_manifests,
)


app = FastAPI(title="Exam Grader V2")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
TEMPLATES = Jinja2Templates(directory=str(TEMPLATE_DIR))

SETTINGS = load_settings(SETTINGS_FILE)
CURRENT_PROJECT: Path | None = None

_elog.init(APP_LOG_DIR)
_elog.log_event("app_started")


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _root_dir() -> Path:
    return Path(SETTINGS["root_dir"])


def _restore_current_project() -> Path | None:
    global CURRENT_PROJECT
    if CURRENT_PROJECT is not None and CURRENT_PROJECT.exists():
        return CURRENT_PROJECT

    last_project = SETTINGS.get("last_project")
    if not last_project:
        return None

    project_dir = resolve_project_dir(_root_dir(), last_project)
    if not (project_dir / "project.json").exists():
        return None

    CURRENT_PROJECT = project_dir.resolve()
    return CURRENT_PROJECT


def _ensure_current_project() -> Path:
    global CURRENT_PROJECT
    restored = _restore_current_project()
    if restored is not None:
        return restored
    if CURRENT_PROJECT is None:
        raise HTTPException(status_code=409, detail="No project is currently open")
    if not CURRENT_PROJECT.exists():
        CURRENT_PROJECT = None
        raise HTTPException(status_code=409, detail="Current project no longer exists")
    return CURRENT_PROJECT


def _paths():
    return project_paths(_ensure_current_project())


def _switch_project(project_dir: Path) -> dict:
    global CURRENT_PROJECT, SETTINGS
    CURRENT_PROJECT = project_dir.resolve()
    metadata = refresh_project_metadata(CURRENT_PROJECT, touch=False)
    _elog.init(project_paths(CURRENT_PROJECT).logs_dir)
    SETTINGS = save_settings(
        SETTINGS_FILE,
        {
            "root_dir": SETTINGS["root_dir"],
            "last_project": metadata["slug"],
        },
    )
    _elog.log_event("project_opened", {"project": metadata["slug"]})
    return metadata


def _safe_project_file(relative_path: str) -> Path:
    base = _paths().root.resolve()
    candidate = (base / relative_path).resolve()
    if not candidate.is_relative_to(base):
        raise HTTPException(status_code=400, detail="Invalid path")
    return candidate


def _pick_directory(initial_dir: str | None) -> str | None:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    selected = filedialog.askdirectory(initialdir=initial_dir or str(_root_dir()))
    root.destroy()
    return selected or None


@app.get("/")
async def project_selector(request: Request):
    return TEMPLATES.TemplateResponse(
        request=request,
        name="project_select.html",
        context={},
    )


@app.get("/dashboard")
async def dashboard(request: Request):
    if _restore_current_project() is None:
        return RedirectResponse(url="/", status_code=303)

    status = get_project_status(_ensure_current_project())
    return TEMPLATES.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "aligned_images": [],
            "has_regions": status["regions"].get("exists", False),
            "template_exists": status["template"]["count"] > 0,
            "templates": status["template"]["files"],
            "project": status["project"],
        },
    )


@app.get("/review")
async def review_page():
    if _restore_current_project() is None:
        return RedirectResponse(url="/", status_code=303)
    return FileResponse(str(STATIC_DIR / "review2.html"), media_type="text/html")


@app.get("/grading")
async def grading_overview(request: Request):
    if _restore_current_project() is None:
        return RedirectResponse(url="/", status_code=303)
    paths = _paths()
    submissions = load_all_submission_results(paths)
    project = refresh_project_metadata(_ensure_current_project(), touch=False)
    return TEMPLATES.TemplateResponse(
        request=request,
        name="grading_overview.html",
        context={"project": project, "submissions": submissions},
    )


@app.get("/grading/student/{student_id}")
async def grading_student(request: Request, student_id: str):
    if _restore_current_project() is None:
        return RedirectResponse(url="/", status_code=303)
    paths = _paths()
    submission = load_submission_result(paths, student_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    for item in submission.get("items", []):
        crop_rel = item.get("crop_path")
        item["student_crop_url"] = f"/api/file?path={crop_rel and ('artifacts/crops/' + crop_rel)}"
    return TEMPLATES.TemplateResponse(
        request=request,
        name="grading_student.html",
        context={"submission": submission, "student_id": student_id},
    )


@app.get("/api/settings")
async def get_settings():
    return SETTINGS


@app.post("/api/settings")
async def update_settings(request: Request):
    global SETTINGS
    payload = await request.json()
    new_root = payload.get("root_dir", SETTINGS.get("root_dir"))
    last_project = SETTINGS.get("last_project")
    if last_project and not resolve_project_dir(Path(new_root), last_project).exists():
        last_project = None

    SETTINGS = save_settings(
        SETTINGS_FILE,
        {
            "root_dir": new_root,
            "last_project": last_project,
        },
    )
    return {"success": True, "settings": SETTINGS}


@app.post("/api/settings/pick-root")
async def pick_root_directory():
    try:
        selected = _pick_directory(SETTINGS.get("root_dir"))
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    if not selected:
        return {"success": False, "cancelled": True}
    return {"success": True, "path": selected}


@app.get("/api/projects")
async def list_projects():
    return {
        "projects": scan_projects(_root_dir()),
        "last_project": SETTINGS.get("last_project"),
    }


@app.post("/api/projects")
async def create_new_project(request: Request):
    payload = await request.json()
    if not payload.get("name"):
        parts = [payload.get("grade"), payload.get("class"), payload.get("subject"), payload.get("exam_name")]
        payload["name"] = " ".join(part for part in parts if part)

    try:
        project = create_project(_root_dir(), payload)
    except FileExistsError as exc:
        return {"success": False, "error": str(exc)}
    except ValueError as exc:
        return {"success": False, "error": str(exc)}

    return {"success": True, "project": project}


@app.post("/api/projects/{slug}/open")
async def open_project(slug: str):
    project_dir = resolve_project_dir(_root_dir(), slug)
    if not (project_dir / "project.json").exists():
        raise HTTPException(status_code=404, detail="Project not found")

    project = _switch_project(project_dir)
    return {"success": True, "project": project, "status": get_project_status(project_dir)}


@app.get("/api/project/current")
async def current_project_info():
    if _restore_current_project() is None:
        return {"project": None}
    return {"project": refresh_project_metadata(_ensure_current_project(), touch=False)}


@app.get("/api/project/status")
async def project_status():
    return get_project_status(_ensure_current_project())


@app.get("/api/files/status")
async def legacy_files_status():
    return get_project_status(_ensure_current_project())


@app.post("/api/upload/template")
async def upload_template(file: UploadFile = File(...)):
    paths = _paths()
    try:
        ext = Path(file.filename).suffix.lower()
        for path in paths.template_dir.glob("blank_*.png"):
            path.unlink()

        if ext in IMG_EXT:
            with open(paths.template_dir / "blank_p1.png", "wb") as target:
                shutil.copyfileobj(file.file, target)
            _elog.log_event("template_uploaded", {"type": "image", "pages": 1})
            refresh_project_metadata(paths.root, touch=True)
            return {"success": True, "pages": 1}

        if ext == ".pdf":
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_pdf = Path(tmp_dir) / "template.pdf"
                with open(tmp_pdf, "wb") as target:
                    shutil.copyfileobj(file.file, target)
                import fitz

                doc = fitz.open(str(tmp_pdf))
                pages_count = len(doc)
                for idx, page in enumerate(doc):
                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(300 / 72, 300 / 72),
                        alpha=False,
                    )
                    pix.save(str(paths.template_dir / f"blank_p{idx + 1}.png"))
                doc.close()

            _elog.log_event("template_uploaded", {"type": "pdf", "pages": pages_count})
            refresh_project_metadata(paths.root, touch=True)
            return {"success": True, "pages": pages_count}

        return {"success": False, "error": f"Unsupported template format: {ext}"}
    except Exception as exc:
        _elog.log_event(
            "template_upload_error",
            {"error": str(exc), "traceback": traceback.format_exc()},
        )
        return {"success": False, "error": str(exc)}


@app.post("/api/upload/answers")
async def upload_answers(file: UploadFile = File(...)):
    paths = _paths()
    try:
        for path in paths.answers_dir.glob("*.pdf"):
            path.unlink()

        target = paths.answers_dir / "answer_key.pdf"
        with open(target, "wb") as out:
            shutil.copyfileobj(file.file, out)

        _elog.log_event("answers_uploaded", {"file": target.name})
        refresh_project_metadata(paths.root, touch=True)
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@app.post("/api/upload/students")
async def upload_students(files: list[UploadFile] = File(...)):
    paths = _paths()
    saved = []
    try:
        for file in files:
            ext = Path(file.filename).suffix.lower()
            if ext == ".pdf":
                out = paths.student_pdf_dir / file.filename
            elif ext in IMG_EXT:
                out = paths.student_page_dir / file.filename
            else:
                continue

            with open(out, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved.append(out.name)

        _elog.log_event("students_uploaded", {"count": len(saved), "files": saved})
        refresh_project_metadata(paths.root, touch=True)
        return {"success": True, "saved": saved}
    except Exception as exc:
        _elog.log_event(
            "students_upload_error",
            {"error": str(exc), "traceback": traceback.format_exc()},
        )
        return {"success": False, "error": str(exc)}


@app.post("/api/run_pipeline")
async def run_pipeline(request: Request):
    paths = _paths()
    templates = list(paths.template_dir.glob("blank_*.png"))
    if not templates:
        return {"success": False, "error": "템플릿 시험지를 먼저 업로드하세요."}

    try:
        payload = await request.json()
        cycle = int(payload.get("cycle", 0))
    except Exception:
        cycle = len(templates)

    pdf_files = list(paths.student_pdf_dir.glob("*.pdf"))
    if pdf_files:
        for path in paths.student_page_dir.glob("*"):
            if path.is_file() and path.suffix.lower() in IMG_EXT:
                path.unlink()
        convert_pdfs_to_images(
            str(paths.student_pdf_dir),
            str(paths.student_page_dir),
            dpi=300,
            cycle=cycle,
        )

    for path in paths.aligned_dir.glob("*"):
        if path.is_file() and path.suffix.lower() in IMG_EXT:
            path.unlink()

    images = [
        path.name
        for path in paths.student_page_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMG_EXT
    ]
    if not images:
        return {"success": False, "error": "정렬할 학생 이미지가 없습니다."}

    ok, fail = 0, 0
    for name in images:
        match = re.search(r"_p(\d+)\.png$", name, re.IGNORECASE)
        if not match:
            match = re.search(r"_page_(\d+)", name, re.IGNORECASE)
        page_num = int(match.group(1)) if match else 1

        target_template = paths.template_dir / f"blank_p{page_num}.png"
        if not target_template.exists():
            target_template = paths.template_dir / "blank_p1.png"

        result = align_image(
            str(paths.student_page_dir / name),
            str(target_template),
            str(paths.aligned_dir / f"aligned_{name}"),
        )
        if result:
            ok += 1
        else:
            fail += 1

    refresh_project_metadata(paths.root, touch=True)
    _elog.log_event("pipeline_done", {"ok": ok, "fail": fail})
    return {"success": True, "aligned": ok, "failed": fail}


@app.get("/api/regions")
async def get_regions():
    paths = _paths()
    data = _load_json(paths.json_dir / "regions.json")
    if data is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "regions.json not found",
                "guide": "Gemini 결과를 붙여 넣어 regions.json을 먼저 저장하세요.",
            },
        )
    _elog.log_event("regions_loaded")
    return data


@app.post("/api/regions")
async def save_regions(request: Request):
    paths = _paths()
    raw = await request.body()
    save_mode = request.query_params.get("mode", "replace_all")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"success": False, "error": f"JSON parse error: {exc}"}

    raw_text = None
    bundle_payload = payload
    if isinstance(payload, dict) and "bundle" in payload:
        bundle_payload = payload.get("bundle", {})
        raw_text = payload.get("raw_text")

    try:
        incoming = normalize_assessment_bundle(bundle_payload)
    except (ValueError, KeyError, TypeError) as exc:
        return {"success": False, "error": str(exc)}

    existing = _load_json(paths.json_dir / "regions.json")
    try:
        data = merge_assessment_bundle(existing, incoming, save_mode)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}

    latest_bundle_path = paths.json_dir / "gemini_bundle_latest.json"
    latest_bundle_path.write_text(
        json.dumps(
            {
                "save_mode": save_mode,
                "bundle": incoming,
                "raw_text": raw_text,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    (paths.json_dir / "regions.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    refresh_project_metadata(paths.root, touch=True)
    question_count = len(data.get("questions", []))
    answer_count = len(data.get("answers", []))
    _elog.log_event("regions_saved", {"count": question_count, "answers": answer_count, "mode": save_mode})
    return {"success": True, "count": question_count, "answers": answer_count, "mode": save_mode}


@app.post("/api/grading/prepare")
async def prepare_grading():
    paths = _paths()
    bundle = _load_json(paths.json_dir / "regions.json")
    if not bundle:
        return {"success": False, "error": "regions.json not found"}

    questions = bundle.get("questions", [])
    if not isinstance(questions, list) or not questions:
        return {"success": False, "error": "questions not found in regions bundle"}

    aligned_files = list_students_from_aligned(paths.aligned_dir)
    grouped = build_submission_manifest(aligned_files)
    manifests = write_submission_manifests(paths, grouped, questions)
    ref_count = generate_reference_crops(paths, questions)
    student_crop_count = generate_student_crops(paths, manifests)

    return {
        "success": True,
        "students": len(manifests),
        "reference_crops": ref_count,
        "student_crops": student_crop_count,
    }


@app.post("/api/grading/ocr")
async def run_ocr():
    paths = _paths()
    try:
        engine = OcrEngine()
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}
    updated = run_ocr_for_project(paths, engine)
    return {"success": True, "updated": updated}


@app.post("/api/grading/score")
async def score_grading_results():
    paths = _paths()
    bundle = _load_json(paths.json_dir / "regions.json")
    if not bundle:
        return {"success": False, "error": "regions.json not found"}
    answers = bundle.get("answers", [])
    if not isinstance(answers, list):
        return {"success": False, "error": "answers not found in regions bundle"}
    if not answers:
        return {"success": False, "error": "No answers saved in regions bundle"}
    count = score_project_submissions(paths, answers)
    return {"success": True, "students": count}


@app.get("/api/file")
async def serve_project_file(path: str):
    full_path = _safe_project_file(path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = None
    if full_path.suffix.lower() == ".png":
        media_type = "image/png"
    elif full_path.suffix.lower() in {".jpg", ".jpeg"}:
        media_type = "image/jpeg"
    return FileResponse(str(full_path), media_type=media_type)


@app.get("/api/templates")
async def list_templates():
    paths = _paths()
    templates = sorted(
        p.name
        for p in paths.template_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMG_EXT and p.name.startswith("blank_")
    )
    return {"pages": templates}


@app.get("/api/template/{name}")
async def serve_template(name: str):
    path = _paths().template_dir / name
    if not path.exists() or not path.name.startswith("blank_"):
        raise HTTPException(status_code=404, detail="Template page not found")
    media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(str(path), media_type=media_type)


@app.get("/api/thumbnail")
async def get_thumbnail(path: str, size: int = 120):
    from fastapi.responses import Response
    import cv2
    import fitz
    import numpy as np

    full_path = _safe_project_file(path)
    if not full_path.exists():
        raise HTTPException(status_code=404)

    ext = full_path.suffix.lower()
    img_data = None

    if ext == ".pdf":
        try:
            doc = fitz.open(str(full_path))
            pix = doc.load_page(0).get_pixmap(
                matrix=fitz.Matrix(150 / 72, 150 / 72),
                alpha=False,
            )
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.h,
                pix.w,
                pix.n,
            )
            if pix.n == 4:
                img_data = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img_data = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            doc.close()
        except Exception:
            raise HTTPException(status_code=500, detail="PDF thumbnail error")
    elif ext in IMG_EXT:
        from aligner import _imread_safe  # type: ignore

        img_data = _imread_safe(str(full_path))
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

    if img_data is not None:
        height, width = img_data.shape[:2]
        new_width = size
        new_height = int(height * (size / width))
        resized = cv2.resize(img_data, (new_width, new_height))
        ok, buf = cv2.imencode(".jpg", resized)
        if ok:
            return Response(content=buf.tobytes(), media_type="image/jpeg")

    raise HTTPException(status_code=500, detail="Thumbnail generation failed")


@app.get("/api/students")
async def list_students():
    paths = _paths()
    files = sorted(
        p.name for p in paths.aligned_dir.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXT
    )
    return {"students": files}


@app.get("/api/student/{name}")
async def serve_aligned(name: str):
    path = _paths().aligned_dir / name
    if not path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(str(path))


@app.delete("/api/student/{name}")
async def delete_student_page(name: str):
    paths = _paths()
    aligned_path = paths.aligned_dir / name
    raw_name = name.replace("aligned_", "")
    raw_path = paths.student_page_dir / raw_name

    deleted = False
    if aligned_path.exists():
        aligned_path.unlink()
        deleted = True
    if raw_path.exists():
        raw_path.unlink()
        deleted = True

    if deleted:
        refresh_project_metadata(paths.root, touch=True)
        _elog.log_event("student_page_deleted", {"file": name})
        return {"success": True}

    raise HTTPException(status_code=404, detail="File not found")


@app.post("/api/student/offset")
async def save_student_offset(request: Request):
    import cv2
    import numpy as np
    from aligner import _imread_safe, _imwrite_safe  # type: ignore

    paths = _paths()
    data = await request.json()
    name = data.get("name")
    dx = int(data.get("dx", 0))
    dy = int(data.get("dy", 0))
    if dx == 0 and dy == 0:
        return {"success": True}

    path = paths.aligned_dir / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    img = _imread_safe(str(path))
    if img is None:
        raise HTTPException(status_code=500, detail="Cannot read image")

    height, width = img.shape[:2]
    matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    shifted = cv2.warpAffine(img, matrix, (width, height), borderValue=(255, 255, 255))
    _imwrite_safe(str(path), shifted)

    _elog.log_event("student_manual_offset", {"file": name, "dx": dx, "dy": dy})
    return {"success": True}


@app.post("/api/student/restore")
async def restore_student_offset(request: Request):
    paths = _paths()
    data = await request.json()
    name = data.get("name")

    raw_name = name.replace("aligned_", "")
    raw_path = paths.student_page_dir / raw_name
    aligned_path = paths.aligned_dir / name
    if not raw_path.exists():
        raise HTTPException(status_code=404, detail="Raw file not found")

    match = re.search(r"_p(\d+)\.png$", raw_name, re.IGNORECASE)
    if not match:
        match = re.search(r"_page_(\d+)", raw_name, re.IGNORECASE)
    page_num = int(match.group(1)) if match else 1

    target_template = paths.template_dir / f"blank_p{page_num}.png"
    if not target_template.exists():
        target_template = paths.template_dir / "blank_p1.png"

    align_image(str(raw_path), str(target_template), str(aligned_path))
    refresh_project_metadata(paths.root, touch=True)
    _elog.log_event("student_restored", {"file": name})
    return {"success": True}


@app.get("/api/student/{name}/raw")
async def serve_raw(name: str):
    raw_name = name.replace("aligned_", "")
    path = _paths().student_page_dir / raw_name
    if not path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(str(path))


@app.post("/api/yolo_save")
async def yolo_save(request: Request):
    paths = _paths()
    payload = await request.json()
    name = payload.get("name", "template")
    questions = payload.get("questions", [])

    lines = []
    for question in questions:
        box = question.get("box", {})
        cx = box["x"] + box["w"] / 2
        cy = box["y"] + box["h"] / 2
        lines.append(f"0 {cx:.6f} {cy:.6f} {box['w']:.6f} {box['h']:.6f}")

    out = paths.yolo_dir / f"{Path(name).stem}.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    refresh_project_metadata(paths.root, touch=True)
    _elog.log_event("review_confirmed", {"file": name, "boxes": len(lines)})
    return {"success": True, "saved": str(out), "boxes": len(lines)}


@app.post("/api/log")
async def frontend_log(request: Request):
    payload = await request.json()
    _elog.log_event(payload.get("event", "frontend"), payload.get("detail", {}))
    return {"success": True}
