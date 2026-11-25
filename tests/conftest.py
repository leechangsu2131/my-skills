"""순수 함수 시험 공통 설정.

    python -m pytest tests -q          (저장소 루트에서)

- 네트워크·Gemini·슈파베이스·실제 지도서 없이 돈다. PDF 는 PyMuPDF 로 그 자리에서 만든다.
- 가져오는 모듈이 import 때 데이터 폴더를 만들므로, 그 전에 임시 폴더로 돌리고 중앙 .env 도 못 찾게 한다
  (내 문서의 실제 데이터·비밀값을 건드리지 않는다).
"""
import os
import pathlib
import sys
import tempfile
import warnings

warnings.filterwarnings("ignore", message=".*fitz.*", category=FutureWarning)   # PyMuPDF: 'import pymupdf 를 쓰라'는 안내

_DATA = tempfile.mkdtemp(prefix="my-skills-test-data-")
os.environ["MY_SKILLS_DATA_DIR"] = _DATA
os.environ["MY_SKILLS_ENV"] = os.path.join(_DATA, "없는.env")
for _key in ("OneDrive", "OneDriveCommercial"):
    os.environ.pop(_key, None)

SKILLS = pathlib.Path(__file__).resolve().parent.parent / "skills"
for _name in ("util-notebooklm", "teacherlesson-assistant", "teacherlesson-guide"):
    sys.path.insert(0, str(SKILLS / _name))
