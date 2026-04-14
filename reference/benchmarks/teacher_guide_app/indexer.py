"""
PDF 인덱서 v2: 한국 초등 교사용 지도서 목차 자동 인식
개선 사항:
  - 목차 페이지 전용 탐지 후 인쇄 페이지->PDF 페이지 오프셋 계산
  - 복합 차시 표현 처리 (1~2차시, 1·2차시)
  - 단원 없는 교과 처리 (음악, 미술, 도덕)
  - 본문 오탐 방지 (목차 페이지 집중 탐색 + 헤더 존만 스캔)
  - Claude AI 프롬프트 대폭 개선
"""

import re
import json
import os
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
from collections import Counter


# ──────────────────────────────────────────────
# 정규식 패턴
# ──────────────────────────────────────────────

UNIT_PATTERNS = [
    (r'(?<!\d)(\d{1,2})\s*단원\b',               'num'),
    (r'제\s*(\d{1,2})\s*단원\b',                  'num'),
    (r'\bUnit\s*(\d{1,2})\b',                    'num'),
    (r'(일|이|삼|사|오|육|칠|팔|구|십)\s*단원\b', 'kor'),
]

LESSON_PATTERNS = [
    (r'(\d{1,2})\s*[~·]\s*(\d{1,2})\s*차시',    'range'),
    (r'제\s*(\d{1,2})\s*차시\b',                 'single'),
    (r'(?<!\d)(\d{1,2})\s*차시\b',              'single'),
    (r'[\[(](\d{1,2})차시[\])]',                 'single'),
    (r'[◆●■▶◎○]\s*(\d{1,2})\s*차시\b',         'single'),
    (r'(\d{1,2})\s*/\s*\d{1,2}\s*차시\b',       'single'),
]

TOC_KEYWORDS = ['차례', '목차', 'contents']
PAGE_REF_RE  = re.compile(r'(\d{1,3})\s*$')
KOR_NUM = {'일':1,'이':2,'삼':3,'사':4,'오':5,'육':6,'칠':7,'팔':8,'구':9,'십':10}


def _kor2int(s): return KOR_NUM.get(s, 0)


class PDFIndexer:

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    # ═══════════════════════════════════════════
    # 공개 진입점
    # ═══════════════════════════════════════════

    def index_pdf(self, pdf_path: str, subject: str, grade: int) -> dict:
        pdf_path = str(pdf_path)
        print(f"  📖 분석 시작: {Path(pdf_path).name}")

        reader = PdfReader(pdf_path)
        total = len(reader.pages)
        print(f"  📄 총 {total}페이지")

        # 1단계: 내장 북마크
        r = self._try_bookmarks(reader)
        if self._valid(r):
            cnt = self._count(r)
            print(f"  ✅ [북마크] {cnt}개 차시")
            return self._finalize(r, subject, grade, total, "bookmarks")

        # 2단계: 목차 페이지
        print(f"  🔍 목차 페이지 탐색...")
        r = self._try_toc_page(pdf_path, reader)
        if self._valid(r):
            cnt = self._count(r)
            print(f"  ✅ [목차 페이지] {cnt}개 차시")
            return self._finalize(r, subject, grade, total, "toc_page")

        # 3단계: 본문 헤더
        print(f"  🔍 본문 헤더 탐색...")
        r = self._try_body_headers(reader)
        if self._valid(r):
            cnt = self._count(r)
            print(f"  ✅ [본문 헤더] {cnt}개 차시")
            return self._finalize(r, subject, grade, total, "body_headers")

        # 4단계: Claude AI
        if self.api_key:
            print(f"  🤖 Claude AI 분석 중...")
            r = self._try_claude(reader, subject, grade)
            if self._valid(r):
                cnt = self._count(r)
                print(f"  ✅ [AI 분석] {cnt}개 차시")
                return self._finalize(r, subject, grade, total, "ai")

        # 5단계: 수동
        print(f"  ⚠️  자동 인식 실패 → 수동 입력 모드")
        return self._manual_input(reader, subject, grade, total)

    # ═══════════════════════════════════════════
    # 1단계: 내장 북마크
    # ═══════════════════════════════════════════

    def _try_bookmarks(self, reader: PdfReader) -> dict | None:
        try:
            if not reader.outline:
                return None
            flat = []
            def flatten(items, depth=0):
                for item in items:
                    if isinstance(item, list):
                        flatten(item, depth+1)
                    else:
                        try:
                            page = reader.get_destination_page_number(item) + 1
                            flat.append((depth, str(item.title), page))
                        except:
                            pass
            flatten(reader.outline)
            return self._assemble_from_bookmarks(flat) if flat else None
        except:
            return None

    def _assemble_from_bookmarks(self, flat: list) -> dict:
        units, current_unit, lesson_list = [], None, []
        for depth, title, page in flat:
            ui = self._det_unit(title)
            li = self._det_lesson(title)
            if ui and depth <= 1:
                current_unit = {"unit_no": ui[0], "title": ui[1],
                                "start_page": page, "lessons": []}
                units.append(current_unit)
            elif li and current_unit:
                lesson = {"lesson_no": li[0], "lesson_no_end": li[1],
                          "title": li[2], "pages": [page, page+7]}
                current_unit["lessons"].append(lesson)
                lesson_list.append((lesson, page))
        # 끝 페이지 보정
        lesson_list.sort(key=lambda x: x[1])
        for i, (lesson, _) in enumerate(lesson_list):
            if i+1 < len(lesson_list):
                lesson["pages"][1] = lesson_list[i+1][1] - 1
        return {"units": units}

    # ═══════════════════════════════════════════
    # 2단계: 목차 페이지
    # ═══════════════════════════════════════════

    def _try_toc_page(self, pdf_path: str, reader: PdfReader) -> dict | None:
        toc_idxs = self._find_toc_pages(reader)
        if not toc_idxs:
            return None

        entries = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for idx in toc_idxs:
                    text = pdf.pages[idx].extract_text(layout=True) or \
                           pdf.pages[idx].extract_text() or ""
                    entries += self._parse_toc_text(text, idx+1)
        except:
            for idx in toc_idxs:
                try:
                    text = reader.pages[idx].extract_text() or ""
                    entries += self._parse_toc_text(text, idx+1)
                except:
                    pass

        if not entries:
            return None

        offset = self._calc_offset(entries, reader)
        return self._assemble_from_toc(entries, offset)

    def _find_toc_pages(self, reader: PdfReader) -> list:
        candidates = []
        scan = min(20, len(reader.pages))
        for i in range(scan):
            try:
                text = (reader.pages[i].extract_text() or "").lower()
                toc_score  = sum(1 for kw in TOC_KEYWORDS if kw in text)
                lesson_cnt = len(re.findall(r'\d+\s*차시', text))
                unit_cnt   = len(re.findall(r'\d+\s*단원', text))
                if toc_score >= 1 or lesson_cnt >= 3 or unit_cnt >= 2:
                    candidates.append(i)
            except:
                pass
        return candidates[:5]

    def _parse_toc_text(self, text: str, src_pdf_page: int) -> list:
        entries = []
        for line in text.split('\n'):
            line = line.strip()
            if not line or len(line) < 3:
                continue

            # 끝의 페이지 번호
            print_page = None
            m = PAGE_REF_RE.search(line)
            if m:
                n = int(m.group(1))
                if 1 <= n <= 999:
                    print_page = n

            ui = self._det_unit(line)
            if ui:
                entries.append({'type':'unit','no':ui[0],'no2':None,
                                'title':ui[1],'print_page':print_page,
                                'src_page':src_pdf_page})
                continue
            li = self._det_lesson(line)
            if li:
                entries.append({'type':'lesson','no':li[0],'no2':li[1],
                                'title':li[2],'print_page':print_page,
                                'src_page':src_pdf_page})
        return entries

    def _calc_offset(self, entries: list, reader: PdfReader) -> int:
        total = len(reader.pages)
        offsets = []
        for e in entries:
            if e['print_page'] and e['src_page']:
                candidate = e['src_page'] - e['print_page']
                if -10 <= candidate <= total:
                    offsets.append(candidate)
        if not offsets:
            return 0
        return Counter(offsets).most_common(1)[0][0]

    def _assemble_from_toc(self, entries: list, offset: int) -> dict:
        units, current_unit, prev_lesson = [], None, None
        for e in entries:
            if e['type'] == 'unit':
                current_unit = {"unit_no": e['no'], "title": e['title'], "lessons": []}
                units.append(current_unit)
                prev_lesson = None
            elif e['type'] == 'lesson':
                pdf_start = (e['print_page'] + offset) if e['print_page'] else e['src_page']
                pdf_start = max(1, pdf_start)
                lesson = {"lesson_no": e['no'], "lesson_no_end": e['no2'] or e['no'],
                          "title": e['title'], "pages": [pdf_start, pdf_start+7]}
                if prev_lesson:
                    prev_lesson["pages"][1] = pdf_start - 1
                if current_unit is None:
                    current_unit = {"unit_no": 1, "title": "전체", "lessons": []}
                    units.append(current_unit)
                current_unit["lessons"].append(lesson)
                prev_lesson = lesson
        return {"units": units}

    # ═══════════════════════════════════════════
    # 3단계: 본문 헤더
    # ═══════════════════════════════════════════

    def _try_body_headers(self, reader: PdfReader) -> dict | None:
        total = len(reader.pages)
        start = min(10, total // 10)
        hits = []  # (pdf_page, type, no, no2, title)

        for i in range(start, total):
            try:
                text = reader.pages[i].extract_text() or ""
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                # 페이지 앞 3줄만 헤더 영역으로 탐색 (본문 오탐 방지)
                for line in lines[:3]:
                    ui = self._det_unit(line)
                    if ui:
                        hits.append((i+1, 'unit', ui[0], None, ui[1]))
                        break
                    li = self._det_lesson(line)
                    if li:
                        hits.append((i+1, 'lesson', li[0], li[1], li[2]))
                        break
            except:
                continue

        if len(hits) < 2:
            return None

        return self._assemble_from_body(hits, total)

    def _assemble_from_body(self, hits: list, total: int) -> dict:
        units, current_unit = [], None
        has_units = any(h[1]=='unit' for h in hits)
        if not has_units:
            current_unit = {"unit_no":1,"title":"전체","lessons":[]}
            units.append(current_unit)

        lesson_pages = [(h[0], h[2], h[3]) for h in hits if h[1]=='lesson']

        for pdf_page, type_, no, no2, title in hits:
            if type_ == 'unit':
                current_unit = {"unit_no":no,"title":title,"lessons":[]}
                units.append(current_unit)
            elif type_ == 'lesson' and current_unit is not None:
                idx = next((i for i,(p,n,n2) in enumerate(lesson_pages)
                            if p==pdf_page and n==no), None)
                if idx is not None and idx+1 < len(lesson_pages):
                    end = lesson_pages[idx+1][0] - 1
                else:
                    end = min(pdf_page+7, total)
                current_unit["lessons"].append({
                    "lesson_no": no, "lesson_no_end": no2 or no,
                    "title": title, "pages": [pdf_page, end]
                })
        return {"units": units}

    # ═══════════════════════════════════════════
    # 4단계: Claude AI
    # ═══════════════════════════════════════════

    def _try_claude(self, reader: PdfReader, subject: str, grade: int) -> dict | None:
        try:
            import anthropic
            total = len(reader.pages)
            texts = []
            for i in range(min(40, total)):
                try:
                    t = reader.pages[i].extract_text() or ""
                    if t.strip():
                        texts.append(f"==[PDF {i+1}p]==\n{t[:600]}")
                except:
                    pass

            combined = "\n".join(texts[:35])
            prompt = f"""초등학교 {grade}학년 {subject} 교사용 지도서 PDF 텍스트입니다.
단원/차시 구조를 파악해 JSON으로만 반환하세요 (설명·마크다운 없음).

규칙:
1. "1~2차시"처럼 복합 차시는 lesson_no=시작번호, lesson_no_end=끝번호
2. 단원이 없으면 unit_no=1, title="전체"로 통합
3. pages=[PDF시작페이지, PDF끝페이지] (1부터 시작, 모를 경우 시작+7 추정)

텍스트:
{combined}

형식:
{{"units":[{{"unit_no":1,"title":"단원명","lessons":[{{"lesson_no":1,"lesson_no_end":2,"title":"1~2차시 제목","pages":[24,31]}}]}}]}}"""

            client = anthropic.Anthropic(api_key=self.api_key)
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2500,
                messages=[{"role":"user","content":prompt}]
            )
            raw = resp.content[0].text.strip()
            raw = re.sub(r'```[a-z]*','',raw).strip('`').strip()
            m = re.search(r'\{[\s\S]*\}', raw)
            if m:
                data = json.loads(m.group())
                for unit in data.get("units",[]):
                    for lesson in unit.get("lessons",[]):
                        if "lesson_no_end" not in lesson:
                            lesson["lesson_no_end"] = lesson["lesson_no"]
                return data
        except Exception as e:
            print(f"  ⚠️  Claude 오류: {e}")
        return None

    # ═══════════════════════════════════════════
    # 5단계: 수동 입력
    # ═══════════════════════════════════════════

    def _manual_input(self, reader: PdfReader, subject: str, grade: int, total: int) -> dict:
        print(f"\n  PDF 총 {total}페이지 | PDF 뷰어로 열어두고 페이지 번호 확인하며 입력하세요.")
        print(f"  (등록 후 'python app.py edit {subject} {grade}' 로 수정 가능)\n")

        unit_count = self._inp_int("  단원 수 (단원 없으면 0)", 0)
        units = []

        if unit_count == 0:
            lesson_count = self._inp_int("  차시 수", 0)
            lessons = []
            for i in range(1, lesson_count+1):
                title = input(f"  {i}차시 제목 (엔터='{i}차시'): ").strip() or f"{i}차시"
                start = self._inp_int(f"  {i}차시 시작 페이지", i*8)
                end   = self._inp_int(f"  {i}차시 끝 페이지",   start+7)
                lessons.append({"lesson_no":i,"lesson_no_end":i,
                                 "title":title,"pages":[start,end]})
            units = [{"unit_no":1,"title":"전체","lessons":lessons}]
        else:
            for u in range(1, unit_count+1):
                unit_title   = input(f"  {u}단원 이름: ").strip() or f"{u}단원"
                lesson_count = self._inp_int(f"  {u}단원 차시 수", 0)
                lessons = []
                for l in range(1, lesson_count+1):
                    title = input(f"    {l}차시 제목 (엔터='{l}차시'): ").strip() or f"{l}차시"
                    start = self._inp_int(f"    {l}차시 시작 페이지", 0)
                    end   = self._inp_int(f"    {l}차시 끝 페이지",   start+7)
                    lessons.append({"lesson_no":l,"lesson_no_end":l,
                                    "title":title,"pages":[start,end]})
                units.append({"unit_no":u,"title":unit_title,"lessons":lessons})

        return {"subject":subject,"grade":grade,"method":"manual",
                "total_pages":total,"units":units}

    # ═══════════════════════════════════════════
    # 감지 헬퍼
    # ═══════════════════════════════════════════

    def _det_unit(self, line: str):
        for pat, typ in UNIT_PATTERNS:
            m = re.search(pat, line)
            if m:
                no = _kor2int(m.group(1)) if typ=='kor' else int(m.group(1))
                if 1 <= no <= 20:
                    return (no, self._clean(line))
        return None

    def _det_lesson(self, line: str):
        for pat, typ in LESSON_PATTERNS:
            m = re.search(pat, line)
            if m:
                no = int(m.group(1))
                no2 = int(m.group(2)) if typ=='range' else no
                if 1 <= no <= 40:
                    return (no, no2, self._clean(line))
        return None

    def _clean(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r'[\s·.]{2,}\d+\s*$', '', text)   # 끝 페이지 번호 제거
        text = re.sub(r'\s+\d{1,3}\s*$', '', text)
        text = text.lstrip('◆●■▶◎○•·-— \t')
        return text[:60].strip() or "제목없음"

    def _inp_int(self, prompt: str, default: int = 0) -> int:
        try:
            v = input(f"{prompt} (기본값 {default}): ").strip()
            return int(v) if v else default
        except:
            return default

    def _valid(self, r) -> bool:
        if not r or not r.get("units"):
            return False
        return sum(len(u.get("lessons",[])) for u in r["units"]) >= 1

    def _count(self, r) -> int:
        return sum(len(u.get("lessons",[])) for u in r.get("units",[]))

    def _finalize(self, r, subject, grade, total, method) -> dict:
        r.update({"subject":subject,"grade":grade,
                  "method":method,"total_pages":total})
        return r
