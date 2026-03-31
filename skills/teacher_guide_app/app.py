#!/usr/bin/env python3
"""
교사용 지도서 PDF 캐시 & 차시 추출 시스템
사용법: python app.py [명령어]
"""

import sys
import os
from pathlib import Path

# 현재 디렉토리를 path에 추가
APP_DIR = Path(__file__).parent
sys.path.insert(0, str(APP_DIR))

# .env 파일 로드 (API 키 설정용)
env_file = APP_DIR / ".env"
if env_file.exists():
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

from indexer import PDFIndexer
from extractor import PDFExtractor
from cache_manager import CacheManager
from ui import CLI

def main():
    cli = CLI()
    cli.run()

if __name__ == "__main__":
    main()
