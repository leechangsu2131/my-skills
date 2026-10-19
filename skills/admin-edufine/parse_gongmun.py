"""
공문서(ODT) 파싱 모듈
- 시행 공문번호/일자, 접수 공문번호/일자, 제목, 수신, 관련 공문번호, 발신처 추출
"""

import re
import sys
from pathlib import Path

try:
    from odf.opendocument import load
    from odf.text import P
    from odf import text as odftext
    from odf.element import Element
    ODL_AVAILABLE = True
except ImportError:
    ODL_AVAILABLE = False

import zipfile
import xml.etree.ElementTree as ET


# ── 텍스트 추출 ──────────────────────────────────────────────────────────────

def extract_text_from_hwpx(filepath: str) -> str:
    """HWPX에서 전체 텍스트를 추출 (zipfile + XML / PrvText 파싱)"""
    texts = []
    try:
        with zipfile.ZipFile(filepath, 'r') as z:
            names = z.namelist()
            # 1. Preview 텍스트가 있으면 활용
            prv_names = [n for n in names if n.lower().endswith('prvtext.txt')]
            if prv_names:
                try:
                    raw_prv = z.read(prv_names[0]).decode('utf-16le', errors='replace')
                    if raw_prv.strip():
                        return raw_prv.strip()
                except Exception:
                    pass

            # 2. Section XML 파싱
            sec_files = sorted([n for n in names if 'section' in n.lower() and n.endswith('.xml')])
            for sec in sec_files:
                with z.open(sec) as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    for elem in root.iter():
                        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                        if tag in ('t', 'p'):
                            t = (elem.text or '').strip()
                            if t:
                                texts.append(t)
    except Exception as e:
        print(f"[HWPX 파싱 오류] {e}")
    return '\n'.join(texts)


def extract_text_from_odt(filepath: str) -> str:
    """ODT에서 전체 텍스트를 추출 (zipfile + XML 직접 파싱)"""
    texts = []
    with zipfile.ZipFile(filepath, 'r') as z:
        with z.open('content.xml') as f:
            tree = ET.parse(f)
    root = tree.getroot()

    # 모든 텍스트 노드를 순서대로 수집
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag in ('p', 'h', 'span', 'a', 'table-cell', 's', 'line-break', 'tab'):
            t = (elem.text or '').strip()
            if t:
                texts.append(t)
    return '\n'.join(texts)


def extract_full_text_flat(filepath: str) -> str:
    """셀 단위 텍스트를 하나의 긴 문자열로 합쳐서 반환 (정규식 매칭용)"""
    ext = Path(filepath).suffix.lower()
    if ext == '.hwpx':
        text = extract_text_from_hwpx(filepath)
        return re.sub(r'\s+', ' ', text)
    
    with zipfile.ZipFile(filepath, 'r') as z:
        if 'content.xml' in z.namelist():
            with z.open('content.xml') as f:
                raw = f.read().decode('utf-8', errors='replace')
            clean = re.sub(r'<[^>]+>', ' ', raw)
            return re.sub(r'\s+', ' ', clean)
    return ""


# ── 파싱 함수들 ──────────────────────────────────────────────────────────────

# 공문번호 패턴: 부서명-숫자  예) 교육지원과-15363, 체육건강과-7694, 화천초등학교-2813
GONGMUN_NO_PATTERN = r'[\w가-힣·]+-\d+'
# 일자 패턴: (2026. 4. 3.) 또는 (2026.4.3.)
DATE_PATTERN = r'\(?\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\s*\.?\s*\)?'


def normalize_date(m, offset: int = 1) -> str:
    """정규식 매치 그룹 -> YYYY-MM-DD. offset = 날짜 첫 그룹 인덱스"""
    return f"{m.group(offset)}-{int(m.group(offset+1)):02d}-{int(m.group(offset+2)):02d}"


def parse_sihaeng(text: str) -> dict:
    """시행 공문번호 + 일자"""
    # group(1)=번호, group(2)=년, group(3)=월, group(4)=일
    m = re.search(r'시행\s*(' + GONGMUN_NO_PATTERN + r')\s*' + DATE_PATTERN, text)
    if m:
        return {
            'sihaeng_no': m.group(1),
            'sihaeng_date': normalize_date(m, offset=2),
        }
    return {}


def parse_jeopsu(text: str) -> dict:
    """접수 공문번호 + 일자"""
    # group(1)=번호, group(2)=년, group(3)=월, group(4)=일
    m = re.search(r'접수\s*(' + GONGMUN_NO_PATTERN + r')\s*' + DATE_PATTERN, text)
    if m:
        return {
            'jeopsu_no': m.group(1),
            'jeopsu_date': normalize_date(m, offset=2),
        }
    return {}


def parse_title(text: str) -> str:
    """제목"""
    m = re.search(r'제\s*목\s+(.+?)(?:\n|시행|접수|수신|$)', text)
    if m:
        return m.group(1).strip()
    return ''


def parse_susin(text: str) -> str:
    """수신"""
    m = re.search(r'수\s*신\s+(.+?)(?:\n|\(경유\)|제목|$)', text)
    if m:
        return m.group(1).strip()
    return ''


def parse_gwanryeon(text: str) -> list:
    """관련 공문번호들 (1. 관련: ... 줄에서 추출)"""
    m = re.search(r'관련\s*[:：]\s*(.+?)(?:\n\d+\.|$)', text, re.DOTALL)
    if not m:
        return []
    snippet = m.group(1)
    return re.findall(GONGMUN_NO_PATTERN + r'\s*' + DATE_PATTERN, snippet)


def parse_balshincheo(text: str) -> str:
    """발신처 (기관명): 테이블 상단 또는 시행 줄 앞"""
    # 테이블 최상단 기관명 패턴 (경상북도○○교육지원청 등)
    m = re.search(r'((?:경상북도|경기도|서울|부산|대구|인천|광주|대전|울산|세종|강원|충북|충남|전북|전남|경남|제주)[\w가-힣]+(?:교육지원청|교육청|학교|청))', text)
    if m:
        return m.group(1)
    return ''


def parse_text_data(lined_text: str, flat_text: str = "", filename: str = "") -> dict:
    """텍스트에서 공문 정보(제목, 발신처, 공문번호 등)를 추출하는 범용 파서"""
    if not flat_text:
        flat_text = re.sub(r'\s+', ' ', lined_text)
    
    result = {}
    result.update(parse_sihaeng(flat_text))
    result.update(parse_jeopsu(flat_text))

    # 문서번호를 찾지 못한 경우 파일명 등에서 패턴 매칭
    if not result.get('sihaeng_no') and not result.get('jeopsu_no') and filename:
        m_file = re.search(r'\(([\w가-힣·]+-\d+)', filename)
        if m_file:
            result['jeopsu_no'] = m_file.group(1)
            result['jeopsu_date'] = ''

    result['제목'] = parse_title(lined_text) or '(제목 미상)'
    result['수신'] = parse_susin(lined_text)
    result['발신처'] = parse_balshincheo(lined_text + ' ' + flat_text)

    # 마감일 키워드 검출 (날짜가 포함된 행 우선)
    deadline_candidates = []
    for line in lined_text.split('\n'):
        if any(kw in line for kw in ['제출기한', '마감일', '제출기일', '신청기한', '접수기간']):
            m_dt = re.search(r'(?:제출기한|마감일|제출기일|신청기한|접수기간)\s*[:：]?\s*([^\n\r]+)', line)
            if m_dt:
                val = m_dt.group(1).strip()
                if val:
                    deadline_candidates.append(val)
    if deadline_candidates:
        result['마감일'] = deadline_candidates[0]
    else:
        # 일반적인 ~까지 패턴
        m_until = re.search(r'(\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?[^\n\r]*?까지)', lined_text)
        result['마감일'] = m_until.group(1).strip() if m_until else ''

    # 관련 공문번호
    gwanryeon = re.findall(
        r'관련\s*[:：]\s*(' + GONGMUN_NO_PATTERN + r')\s*' + DATE_PATTERN,
        flat_text
    )
    result['관련공문'] = [
        {'번호': g[0], '일자': f"{g[1]}-{int(g[2]):02d}-{int(g[3]):02d}"}
        for g in gwanryeon
    ]
    result['raw_text'] = lined_text
    return result


def parse_odt(filepath: str) -> dict:
    """ODT 공문 파싱 메인 함수 - 모든 필드 반환"""
    lined_text = extract_text_from_odt(filepath)
    flat_text = extract_full_text_flat(filepath)
    filename = Path(filepath).name
    return parse_text_data(lined_text, flat_text, filename)


def parse_hwpx(filepath: str) -> dict:
    """HWPX 공문 파싱"""
    lined_text = extract_text_from_hwpx(filepath)
    flat_text = extract_full_text_flat(filepath)
    filename = Path(filepath).name
    return parse_text_data(lined_text, flat_text, filename)


def parse_document(filepath: str) -> dict:
    """확장자에 맞춰 문서를 자동 파싱"""
    ext = Path(filepath).suffix.lower()
    if ext == '.odt':
        return parse_odt(filepath)
    elif ext == '.hwpx':
        return parse_hwpx(filepath)
    elif ext in ('.txt', '.log'):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='cp949', errors='replace') as f:
                content = f.read()
        return parse_text_data(content, filename=Path(filepath).name)
    else:
        # 지원되지 않는 파일은 기본 텍스트 파싱 시도
        return {
            '제목': Path(filepath).stem,
            '발신처': '',
            'sihaeng_no': '',
            'sihaeng_date': '',
            'jeopsu_no': '',
            'jeopsu_date': '',
            '마감일': '',
            '관련공문': [],
            'raw_text': ''
        }


def generate_edufine_draft(parsed_data: dict, custom_memo: str = "", item_list: str = "") -> dict:
    """
    파싱된 정보와 사용자 메모/물품목록을 바탕으로 K-에듀파인 표준 규격 기안문(제목, 본문) 자동 생성
    """
    sender = parsed_data.get('발신처', '')
    orig_title = parsed_data.get('제목', '공문 관련 업무')
    sihaeng_no = parsed_data.get('sihaeng_no', '')
    sihaeng_date = parsed_data.get('sihaeng_date', '').replace('-', '.')
    jeopsu_no = parsed_data.get('jeopsu_no', '')
    jeopsu_date = parsed_data.get('jeopsu_date', '').replace('-', '.')
    deadline = parsed_data.get('마감일', '')
    related_docs = parsed_data.get('관련공문', [])

    # 1. 기안문 제목 생성 (목적/행위 중심 명사형 종결)
    clean_title = re.sub(r'^(안내|알림|요청|제출|협조|공문)[\s:：]+', '', orig_title).strip()
    clean_title = re.sub(r'[\(\[\<][^\)\]\>]+[\)\]\>]', '', clean_title).strip()
    
    if item_list:
        draft_title = f"{clean_title} 관련 물품 구매(품의) 계획"
    elif any(kw in orig_title for kw in ['계획', '실시', '운영']):
        draft_title = f"{clean_title} 추진 및 제출 계획"
    elif any(kw in orig_title for kw in ['신청', '추천', '희망']):
        draft_title = f"{clean_title} 참가 희망자 명단 제출"
    elif any(kw in orig_title for kw in ['조사', '제출']):
        draft_title = f"{clean_title} 결과 및 실적 제출"
    else:
        draft_title = f"{clean_title} 관련 추진 계획"

    # 2. 본문 1항 (관련 근거)
    ref_str = ""
    if sender and sihaeng_no and sihaeng_date:
        ref_str = f"{sender}-{sihaeng_no}({sihaeng_date}.)"
    elif sihaeng_no and sihaeng_date:
        ref_str = f"대호-{sihaeng_no}({sihaeng_date}.)"
    elif jeopsu_no and jeopsu_date:
        ref_str = f"본교-{jeopsu_no}({jeopsu_date}.)"
    elif related_docs:
        ref_str = f"{related_docs[0]['번호']}({related_docs[0]['일자'].replace('-', '.')}.)"

    body_lines = []
    if ref_str:
        body_lines.append(f"1. 관련: {ref_str}호")
    else:
        body_lines.append("1. 관련: 귀 기관 공문 관련 근거")

    # 3. 본문 2항 (목적 및 세부 계획 / 물품 구매)
    if item_list:
        body_lines.append(f"2. 위 호와 관련하여, {clean_title}에 필요한 물품을 다음과 같이 구입(품의)하고자 합니다.")
        # 첫 번째 품목 이름 추정
        first_item = item_list.strip().split('\n')[0].split('\t')[0].strip()
        body_lines.append(f"  가. 건명: {first_item} 외 물품 구매")
        body_lines.append(f"  나. 용도: {clean_title} 운영 및 교육활동 활용")
        body_lines.append("  다. 구매방법: S2B(학교장터) 전자조달 구매")
        if custom_memo:
            body_lines.append(f"  라. 주요내용: {custom_memo}")
        body_lines.append("  마. 세부내역: 품의명세서(붙임) 참조")
        body_lines.append("3. 행정사항: 관련 예산 집행 품의 후 구매 진행")
        body_lines.append("")
        body_lines.append("붙임  1. 지출(지급)품의서 1부.  끝.")
    else:
        body_lines.append(f"2. 위 호와 관련하여, {clean_title}을(를) 다음과 같이 추진(제출)하고자 합니다.")
        body_lines.append(f"  가. 사업(업무)명: {clean_title}")
        body_lines.append(f"  나. 주요 대상: 본교 해당 학생 및 교직원")
        if custom_memo:
            body_lines.append(f"  다. 세부내용: {custom_memo}")
        else:
            body_lines.append(f"  다. 세부내용: 세부 계획 및 제출 명단 붙임 참조")
        
        # 3항 (행정사항)
        body_lines.append("3. 행정사항")
        if deadline:
            body_lines.append(f"  가. 제출기한: {deadline}")
        else:
            body_lines.append("  가. 제출기한: 공문 접수 기한 내")
        body_lines.append("  나. 제출방법: K-에듀파인 전자결재 문서 제출")
        body_lines.append("")
        body_lines.append(f"붙임  1. {clean_title} 관련 서식 1부.  끝.")

    draft_body = "\n".join(body_lines)

    return {
        'title': draft_title,
        'body': draft_body,
        'parsed_info': parsed_data
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    filepath = sys.argv[1] if len(sys.argv) > 1 else \
        '/mnt/user-data/uploads/_화천초등학교-2813__본문__경상북도경주교육지원청_교육지원과___교부_안내__2026년_학교_체육시설_개선_사업비_교부.odt'

    result = parse_odt(filepath)

    print("=" * 50)
    print("📄 공문 파싱 결과")
    print("=" * 50)
    print(f"  발신처       : {result.get('발신처', '추출 실패')}")
    print(f"  제목         : {result.get('제목', '추출 실패')}")
    print(f"  수신         : {result.get('수신', '추출 실패')}")
    print(f"  시행 공문번호 : {result.get('sihaeng_no', '추출 실패')}")
    print(f"  시행 일자     : {result.get('sihaeng_date', '추출 실패')}")
    print(f"  접수 공문번호 : {result.get('jeopsu_no', '추출 실패')}")
    print(f"  접수 일자     : {result.get('jeopsu_date', '추출 실패')}")
    if result.get('관련공문'):
        for g in result['관련공문']:
            print(f"  관련 공문     : {g['번호']} ({g['일자']})")
    print("=" * 50)
