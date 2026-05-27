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

def extract_text_from_odt(filepath: str) -> str:
    """ODT에서 전체 텍스트를 추출 (zipfile + XML 직접 파싱)"""
    texts = []
    with zipfile.ZipFile(filepath, 'r') as z:
        with z.open('content.xml') as f:
            tree = ET.parse(f)
    root = tree.getroot()

    # 모든 텍스트 노드를 순서대로 수집
    ns = {'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag in ('p', 'h', 'span', 'a', 'table-cell', 's', 'line-break', 'tab'):
            t = (elem.text or '').strip()
            if t:
                texts.append(t)
            # tail은 부모 수집 시 중복되므로 생략
    return '\n'.join(texts)


def extract_full_text_flat(filepath: str) -> str:
    """셀 단위 텍스트를 하나의 긴 문자열로 합쳐서 반환 (정규식 매칭용)"""
    with zipfile.ZipFile(filepath, 'r') as z:
        with z.open('content.xml') as f:
            raw = f.read().decode('utf-8')
    # XML 태그 제거
    clean = re.sub(r'<[^>]+>', ' ', raw)
    # 연속 공백 정리
    clean = re.sub(r'\s+', ' ', clean)
    return clean


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


def parse_odt(filepath: str) -> dict:
    """ODT 공문 파싱 메인 함수 - 모든 필드 반환"""
    # 두 가지 텍스트 형태 준비
    lined_text = extract_text_from_odt(filepath)
    flat_text = extract_full_text_flat(filepath)

    result = {}
    result.update(parse_sihaeng(flat_text))
    result.update(parse_jeopsu(flat_text))
    
    # 텍스트에서 문서번호를 찾지 못한 경우, 파일명에서 추출 시도 (예: (화천초등학교-4112 (본문))...)
    if not result.get('sihaeng_no') and not result.get('jeopsu_no'):
        filename = Path(filepath).name
        m_file = re.search(r'\(([\w가-힣·]+-\d+)', filename)
        if m_file:
            # 파일명에 날짜는 없으므로 번호만 임시로 접수번호로 사용
            result['jeopsu_no'] = m_file.group(1)
            # 날짜를 모를 때는 일단 공백으로 두거나 오늘 날짜 등을 쓸 수 있음
            result['jeopsu_date'] = ''
            
    result['제목'] = parse_title(lined_text)
    result['수신'] = parse_susin(lined_text)
    result['발신처'] = parse_balshincheo(lined_text + flat_text)

    # 관련 공문번호
    gwanryeon = re.findall(
        r'관련\s*[:：]\s*(' + GONGMUN_NO_PATTERN + r')\s*' + DATE_PATTERN,
        flat_text
    )
    result['관련공문'] = [
        {'번호': g[0], '일자': f"{g[1]}-{int(g[2]):02d}-{int(g[3]):02d}"}
        for g in gwanryeon
    ]

    return result


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
