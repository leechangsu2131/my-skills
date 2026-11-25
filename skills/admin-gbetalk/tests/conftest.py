"""admin-gbetalk 시험 공통 설정.

gbtalk_summary.py 는 불러오는 순간 data_dir(...) 로 폴더를 만든다. 시험이 교사 PC 의 실제 데이터 폴더
(내 문서\\my-skills-data)나 중앙 .env 를 건드리지 않도록, 시험 프로세스에서만 데이터 폴더를 임시 폴더로 돌린다.
모듈을 불러오기 전에 실행돼야 하므로 conftest 맨 위에서 한다. 실제 쪽지·발송 코드는 시험에서 실행하지 않는다.
"""
import atexit
import os
import shutil
import tempfile

_DATA = tempfile.mkdtemp(prefix="gbetalk-test-data-")
os.environ["MY_SKILLS_DATA_DIR"] = _DATA
atexit.register(shutil.rmtree, _DATA, ignore_errors=True)
