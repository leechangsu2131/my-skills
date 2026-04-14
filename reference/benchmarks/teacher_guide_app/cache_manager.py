"""
캐시 관리: PDF 파일과 인덱스 메타데이터를 저장/불러오기
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime


SUBJECTS = {
    "국어": "korean",
    "수학": "math",
    "과학": "science",
    "사회": "social",
    "영어": "english",
    "도덕": "moral",
    "음악": "music",
    "미술": "art",
    "체육": "pe",
    "실과": "practical",
}

SUBJECT_ALIASES = {
    "국": "국어", "수": "수학", "과": "과학", "사": "사회",
    "영": "영어", "도": "도덕", "음": "음악", "미": "미술",
    "체": "체육", "실": "실과",
}


class CacheManager:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            # 앱과 같은 디렉토리에 cache 폴더 생성
            app_dir = Path(__file__).parent
            base_dir = app_dir / "cache"
        self.base_dir = Path(base_dir)
        self.registry_path = self.base_dir / "registry.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._init_registry()

    def _init_registry(self):
        if not self.registry_path.exists():
            self._save_registry({})

    def _load_registry(self) -> dict:
        with open(self.registry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_registry(self, data: dict):
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def normalize_subject(self, subject: str) -> str:
        """교과명 정규화 (별칭 처리)"""
        subject = subject.strip()
        if subject in SUBJECT_ALIASES:
            subject = SUBJECT_ALIASES[subject]
        return subject

    def get_cache_key(self, subject: str, grade: int) -> str:
        subject = self.normalize_subject(subject)
        eng = SUBJECTS.get(subject, subject.lower())
        return f"{eng}_{grade}grade"

    def get_cache_dir(self, subject: str, grade: int) -> Path:
        key = self.get_cache_key(subject, grade)
        d = self.base_dir / key
        d.mkdir(parents=True, exist_ok=True)
        return d

    def register_pdf(self, subject: str, grade: int, pdf_path: str) -> Path:
        """PDF를 캐시에 등록하고 복사본 저장"""
        cache_dir = self.get_cache_dir(subject, grade)
        dest = cache_dir / "source.pdf"
        if str(pdf_path) != str(dest):
            shutil.copy2(pdf_path, dest)

        registry = self._load_registry()
        key = self.get_cache_key(subject, grade)
        registry[key] = {
            "subject": self.normalize_subject(subject),
            "grade": grade,
            "original_name": Path(pdf_path).name,
            "registered_at": datetime.now().isoformat(),
            "indexed": False,
        }
        self._save_registry(registry)
        return dest

    def save_meta(self, subject: str, grade: int, meta: dict):
        """차시 인덱스 메타데이터 저장"""
        cache_dir = self.get_cache_dir(subject, grade)
        meta_path = cache_dir / "meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 레지스트리에 indexed 표시
        registry = self._load_registry()
        key = self.get_cache_key(subject, grade)
        if key in registry:
            registry[key]["indexed"] = True
            registry[key]["unit_count"] = len(meta.get("units", []))
            self._save_registry(registry)

    def load_meta(self, subject: str, grade: int) -> dict | None:
        """차시 인덱스 메타데이터 불러오기"""
        cache_dir = self.get_cache_dir(subject, grade)
        meta_path = cache_dir / "meta.json"
        if not meta_path.exists():
            return None
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_pdf_path(self, subject: str, grade: int) -> Path | None:
        """캐시된 PDF 경로 반환"""
        cache_dir = self.get_cache_dir(subject, grade)
        pdf = cache_dir / "source.pdf"
        return pdf if pdf.exists() else None

    def list_registered(self) -> list:
        """등록된 교과서 목록"""
        registry = self._load_registry()
        return list(registry.values())

    def is_registered(self, subject: str, grade: int) -> bool:
        registry = self._load_registry()
        key = self.get_cache_key(subject, grade)
        return key in registry

    def find_lesson(self, subject: str, grade: int, unit_no: int, lesson_no: int) -> dict | None:
        """차시 정보 검색 → 페이지 범위 반환
        복합 차시(1~2차시)의 경우 lesson_no가 범위 안에 있으면 매칭"""
        meta = self.load_meta(subject, grade)
        if not meta:
            return None

        for unit in meta.get("units", []):
            if unit.get("unit_no") == unit_no:
                for lesson in unit.get("lessons", []):
                    start_no = lesson.get("lesson_no", 0)
                    end_no   = lesson.get("lesson_no_end", start_no)
                    # 단일 차시 또는 복합 차시 범위 매칭
                    if start_no <= lesson_no <= end_no:
                        return {
                            "subject": subject,
                            "grade": grade,
                            "unit_no": unit_no,
                            "unit_title": unit.get("title", ""),
                            "lesson_no": lesson_no,
                            "lesson_no_end": end_no,
                            "lesson_title": lesson.get("title", ""),
                            "pages": lesson.get("pages", []),
                        }
        return None

    def search_lessons(self, subject: str, grade: int, keyword: str) -> list:
        """키워드로 차시 검색"""
        meta = self.load_meta(subject, grade)
        if not meta:
            return []

        results = []
        for unit in meta.get("units", []):
            for lesson in unit.get("lessons", []):
                if keyword in lesson.get("title", "") or keyword in unit.get("title", ""):
                    results.append({
                        "unit_no": unit.get("unit_no"),
                        "unit_title": unit.get("title", ""),
                        "lesson_no": lesson.get("lesson_no"),
                        "lesson_title": lesson.get("title", ""),
                        "pages": lesson.get("pages", []),
                    })
        return results
