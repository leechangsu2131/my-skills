"""
차시 내용 분석기: Claude API로 지도서 내용을 수업 준비용으로 요약
"""

import os
import re
import json
from pathlib import Path
from pypdf import PdfReader
import pdfplumber


ANALYSIS_PROMPT = """당신은 초등학교 교사를 돕는 수업 준비 도우미입니다.
아래는 교사용 지도서의 특정 차시 내용입니다. 교사가 수업 전 빠르게 파악할 수 있도록 핵심 내용을 정리해주세요.

교과: {subject} / 학년: {grade}학년 / {unit_no}단원 {lesson_no}차시
단원명: {unit_title} / 차시명: {lesson_title}
페이지: {start_page}~{end_page}

---
{content}
---

다음 형식으로 정리해주세요:

## 🎯 학습 목표
(이 차시에서 학생들이 배울 핵심 목표 2~3가지)

## 📋 수업 흐름
(도입 → 전개 → 정리 순서로 간략히)

## 💡 핵심 내용
(꼭 알아야 할 개념이나 내용 3~5가지 bullet)

## ✏️ 주요 활동
(학생 활동 위주로 정리)

## ⚠️ 지도 유의사항
(교사가 특히 주의할 점, 없으면 생략)

한국어로 간결하게 작성하되, 교사가 수업 직전 5분 안에 읽고 바로 활용할 수 있는 수준으로 써주세요."""


class LessonAnalyzer:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    def extract_text_from_pages(self, pdf_path: str, start_page: int, end_page: int) -> str:
        """지정된 페이지 범위에서 텍스트 추출"""
        text_parts = []

        try:
            # pdfplumber로 레이아웃 보존 추출 시도
            with pdfplumber.open(pdf_path) as pdf:
                total = len(pdf.pages)
                s = max(0, start_page - 1)
                e = min(total, end_page)
                for i in range(s, e):
                    page = pdf.pages[i]
                    text = page.extract_text(layout=True) or ""
                    if text.strip():
                        text_parts.append(f"[{i+1}페이지]\n{text}")
        except Exception:
            # fallback: pypdf
            try:
                reader = PdfReader(pdf_path)
                total = len(reader.pages)
                s = max(0, start_page - 1)
                e = min(total, end_page)
                for i in range(s, e):
                    text = reader.pages[i].extract_text() or ""
                    if text.strip():
                        text_parts.append(f"[{i+1}페이지]\n{text}")
            except Exception as ex:
                return f"텍스트 추출 실패: {ex}"

        combined = "\n\n".join(text_parts)
        # 토큰 절약: 최대 6000자
        if len(combined) > 6000:
            combined = combined[:6000] + "\n...(이하 생략)"
        return combined

    def analyze(self, pdf_path: str, lesson_info: dict) -> str:
        """차시 내용을 Claude API로 분석"""
        if not self.api_key:
            return self._no_api_fallback(lesson_info)

        pages = lesson_info.get("pages", [1, 8])
        content = self.extract_text_from_pages(str(pdf_path), pages[0], pages[1])

        if not content.strip() or "텍스트 추출 실패" in content:
            return self._scanned_pdf_notice(lesson_info)

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)

            prompt = ANALYSIS_PROMPT.format(
                subject=lesson_info.get("subject", ""),
                grade=lesson_info.get("grade", ""),
                unit_no=lesson_info.get("unit_no", ""),
                lesson_no=lesson_info.get("lesson_no", ""),
                unit_title=lesson_info.get("unit_title", ""),
                lesson_title=lesson_info.get("lesson_title", ""),
                start_page=pages[0],
                end_page=pages[1],
                content=content
            )

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text

        except Exception as e:
            return f"⚠️ 분석 오류: {e}\n\n추출된 텍스트:\n{content[:1000]}"

    def _no_api_fallback(self, lesson_info: dict) -> str:
        return (
            f"⚠️ API 키가 없어 자동 분석을 사용할 수 없습니다.\n\n"
            f"환경변수 ANTHROPIC_API_KEY를 설정하면\n"
            f"차시 내용 자동 요약 기능을 사용할 수 있습니다.\n\n"
            f"설정 방법:\n"
            f"  Mac/Linux: export ANTHROPIC_API_KEY='sk-ant-...'\n"
            f"  Windows:   set ANTHROPIC_API_KEY=sk-ant-..."
        )

    def _scanned_pdf_notice(self, lesson_info: dict) -> str:
        pages = lesson_info.get("pages", [1, 8])
        return (
            f"⚠️ 이 PDF는 스캔본이거나 텍스트 추출이 불가능합니다.\n\n"
            f"해당 차시 페이지: {pages[0]}~{pages[1]}\n"
            f"추출된 PDF 파일을 직접 열어서 내용을 확인해주세요.\n\n"
            f"※ 스캔본 PDF의 경우 OCR 처리가 필요합니다.\n"
            f"  (향후 업데이트에서 지원 예정)"
        )
