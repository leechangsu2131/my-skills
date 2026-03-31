#!/bin/bash
# 교사용 지도서 PDF 관리 시스템 - 설치 스크립트

echo "========================================"
echo "  📚 교사용 지도서 PDF 관리 시스템"
echo "  설치 스크립트"
echo "========================================"
echo ""

# Python 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되어 있지 않습니다."
    echo "   https://python.org 에서 Python 3.10 이상을 설치해주세요."
    exit 1
fi

echo "✅ Python: $(python3 --version)"

# pip 패키지 설치
echo ""
echo "📦 필요한 패키지 설치 중..."
pip3 install pypdf pdfplumber anthropic rich

# .env 파일 생성 안내
echo ""
if [ ! -f ".env" ]; then
    echo "# Anthropic API 키 설정 (수업 내용 AI 요약 기능용)" > .env
    echo "# ANTHROPIC_API_KEY=sk-ant-여기에-키를-입력하세요" >> .env
    echo "📝 .env 파일을 생성했습니다."
fi

echo ""
echo "========================================"
echo "  ✅ 설치 완료!"
echo "========================================"
echo ""
echo "▶ AI 분석 기능 사용 시 .env 파일을 열어 API 키를 입력하세요:"
echo "  ANTHROPIC_API_KEY=sk-ant-xxxxxxxxx"
echo ""
echo "▶ 시작하기"
echo "  python3 app.py help    # 도움말"
echo "  python3 app.py         # 대화형 모드"
echo ""
