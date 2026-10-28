"""Shared PKM utilities for the Obsidian property manager."""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


INDEX_MAPPING = {
    "나에 대한 이해": {"domain": "자기", "engine": "concept"},
    "생각 습관 개선": {"domain": "자기", "engine": "principle"},
    "성장 마인드셋": {"domain": "자기", "engine": "concept"},
    "행동 습관 바꾸기": {"domain": "자기", "engine": "principle"},
    "멘탈훈련": {"domain": "자기", "engine": "experiment"},
    "선택과 후회 ft 의사결정": {"domain": "자기", "engine": "pattern"},
    "PESM 증후군": {"domain": "자기", "engine": "concept"},
    "5단계 연꽃 기법": {"domain": "자기", "engine": "experiment"},
    "국어 수업 IDEA": {"domain": "수업", "engine": "experiment"},
    "역사 수업 idea": {"domain": "수업", "engine": "experiment"},
    "개념기반교육과정": {"domain": "수업", "engine": "concept"},
    "문학기반 인성교육": {"domain": "수업", "engine": "concept"},
    "정반합을 위한 토론": {"domain": "수업", "engine": "experiment"},
    "가르치고 싶은 것": {"domain": "수업", "engine": "principle"},
    "수업을 위한 기초 소양": {"domain": "수업", "engine": "principle"},
    "생각하는 힘": {"domain": "수업", "engine": "concept"},
    "학급 운영": {"domain": "학급", "engine": "principle"},
    "학생과 감정싸움하지말고 규칙을 세워 적용하자": {"domain": "학급", "engine": "principle"},
    "담보를 받자 학생에게": {"domain": "학급", "engine": "experiment"},
    "얍삽한 학생 대처 방안": {"domain": "학급", "engine": "pattern"},
    "학급에서 스트레스 받는 경우": {"domain": "학급", "engine": "pattern"},
    "이지메의 구조": {"domain": "학급", "engine": "concept"},
    "장악력": {"domain": "학급", "engine": "principle"},
    "교실 문화의 변화": {"domain": "학급", "engine": "concept"},
    "다른 선생님을 그리워하는 학생들": {"domain": "학급", "engine": "pattern"},
    "행정실 교사 소통": {"domain": "학급", "engine": "principle"},
    "직관 vs 데이터": {"domain": "자기", "engine": "pattern"},
    "복리의 문제해결력": {"domain": "자기", "engine": "concept"},
    "왜라는 질문을 하고 문제를 해결하자": {"domain": "자기", "engine": "principle"},
    "결정을 번복하지 않으려면": {"domain": "자기", "engine": "principle"},
    "판단과 비논리적해결 분석과 논리적해결": {"domain": "자기", "engine": "pattern"},
    "매개 평가프로토콜": {"domain": "자기", "engine": "experiment"},
    "결정 관찰자를 위한 점검표": {"domain": "자기", "engine": "experiment"},
    "하방은 지지되고 상방이 열려있는 선택하기": {"domain": "투자", "engine": "pattern"},
    "예측수정": {"domain": "투자", "engine": "experiment"},
    "정보의 해석, 수집 반영": {"domain": "투자", "engine": "principle"},
    "사람 마음 얻는법 관계적 roic": {"domain": "관계", "engine": "principle"},
    "리더쉽": {"domain": "관계", "engine": "principle"},
    "논쟁에서 이기기 위한 프레임": {"domain": "관계", "engine": "pattern"},
    "입지를 좁히는 사람들": {"domain": "관계", "engine": "pattern"},
    "설득력을 키우자": {"domain": "관계", "engine": "principle"},
    "부부갈등 해결 결혼 나영": {"domain": "관계", "engine": "experiment"},
    "나는 왜 무시를 쉽게 받는가": {"domain": "자기", "engine": "concept"},
    "사랑": {"domain": "자기", "engine": "concept"},
    "글쓰기": {"domain": "생산성", "engine": "principle"},
    "인지적 구두쇠 이론": {"domain": "자기", "engine": "concept"},
    "기질의 4요소": {"domain": "자기", "engine": "concept"},
    "진화심리학": {"domain": "자기", "engine": "concept"},
    "동양철학": {"domain": "자기", "engine": "concept"},
    "파레토의 법칙": {"domain": "자기", "engine": "concept"},
    "동조효과와 소수의견": {"domain": "관계", "engine": "concept"},
    "여러 모형들": {"domain": "투자", "engine": "concept"},
    "원칙 - 레이달리오": {"domain": "투자", "engine": "principle"},
    "쏠림현상": {"domain": "투자", "engine": "concept"},
    "기저효과 베이즈 정리": {"domain": "투자", "engine": "concept"},
    "투자일지": {"domain": "투자", "engine": "experiment"},
    "투자와 관련된 이론 철학, 상황": {"domain": "투자", "engine": "concept"},
    "캘리기준": {"domain": "투자", "engine": "principle"},
    "자본의 힘": {"domain": "투자", "engine": "concept"},
    "경제 매크로 해석": {"domain": "투자", "engine": "concept"},
    "ai투자": {"domain": "투자", "engine": "experiment"},
    "스톡데일 패러독스": {"domain": "투자", "engine": "pattern"},
    "절세 전략 세금": {"domain": "투자", "engine": "experiment"},
    "대출": {"domain": "투자", "engine": "experiment"},
    "비트코인": {"domain": "투자", "engine": "concept"},
    "diy": {"domain": "DIY", "engine": "experiment"},
    "리콴유가 본 세계": {"domain": "자기", "engine": "concept"},
    "국가발전의 원리": {"domain": "자기", "engine": "concept"},
    "사회에 대한 생각들": {"domain": "자기", "engine": "concept"},
}

DOMAIN_VALUES = ["수업", "학급", "투자", "자기", "관계", "DIY", "생산성", "횡단"]
ENGINE_VALUES = ["concept", "pattern", "principle", "experiment"]
TYPE_VALUES = ["수업안", "감상문", "거시예측", "시장일지", "자서전", "리소스"]

PROP_DESCRIPTIONS = {
    "domain": "삶의 영역\n수업/학급/투자/자기/관계/DIY/생산성/횡단",
    "engine": "사고 단계\nconcept(개념) / pattern(패턴)\nprinciple(원칙) / experiment(실험)",
    "topic": "짧은 주제어 (자유 입력)\n예: 학급갈등, 안전마진, 교육연극",
    "type": "노트 유형\n수업안 / 감상문 / 거시예측 / 시장일지 / 자서전 / 리소스",
    "status": "진행 상태\n완료 / 초안 / 진행중 / 확인됨 / 반증됨 / 철회",
    "관련종목": "관련 종목 (리스트)\n예: tsmc, 삼성전자\n[a, b] 형식으로 저장됨",
    "확률": "예측 확률 (0.0 ~ 1.0)",
    "중요도": "중요도 숫자 (예: 12)",
    "확인시기": "확인 예정 시기 (예: 2025-06)",
    "상태": "거시예측 상태\n진행중 / 확인됨 / 반증됨 / 철회",
    "날짜": "시장일지 날짜 (예: 2025-10)",
}

READ_ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")


def read_text_file(path: Path) -> str:
    last_error = None  # type: Optional[Exception]
    for encoding in READ_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return path.read_text(encoding="utf-8")


def backup_file(path: Path) -> Path:
    """변경 전 .bak 백업 생성 (절대 삭제 없음 원칙)"""
    bak_dir = path.parent / "_PKM_BACKUP"
    bak_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_path = bak_dir / f"{path.stem}_{ts}{path.suffix}.bak"
    shutil.copy2(path, bak_path)
    return bak_path


def parse_yaml_value(raw: str):
    v = raw.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1]
        if not inner.strip():
            return []
        items = [item.strip().strip("'\"") for item in inner.split(",")]
        return items if len(items) > 1 else (items[0] if items else "")
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    return v


def format_yaml_value(val) -> str:
    if isinstance(val, list):
        if not val:
            return "[]"
        return "[" + ", ".join(str(item) for item in val) + "]"
    s = str(val)
    if any(c in s for c in [":", "#", '"', "'", "[", "]", "{"]):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def read_frontmatter(text: str):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.DOTALL)
    if not m:
        return {}, [], text

    raw = m.group(1)
    body = text[m.end():]
    lines = raw.splitlines()
    props = {}
    blocks = []

    i = 0
    while i < len(lines):
        line = lines[i]
        simple = re.match(r"^([\w가-힣]+)\s*:\s*(.*)$", line)
        if simple:
            key, value = simple.group(1), simple.group(2).strip()

            if value == "" and i + 1 < len(lines) and re.match(r"^\s+-\s", lines[i + 1]):
                block_lines = [line]
                list_items = []
                i += 1
                while i < len(lines) and re.match(r"^\s+-\s?(.*)", lines[i]):
                    item_m = re.match(r"^\s+-\s?(.*)", lines[i])
                    list_items.append(item_m.group(1).strip().strip("'\""))
                    block_lines.append(lines[i])
                    i += 1
                props[key] = list_items if len(list_items) != 1 else list_items[0]
                blocks.append({"key": key, "lines": block_lines, "is_list_block": True})
                continue

            parsed = parse_yaml_value(value)
            if isinstance(parsed, str) and "," in parsed and not re.match(r"^\d", parsed):
                items = [item.strip() for item in parsed.split(",") if item.strip()]
                if len(items) > 1:
                    parsed = items
            props[key] = parsed
            blocks.append({"key": key, "lines": [line], "is_list_block": False})
        else:
            blocks.append({"key": None, "lines": [line], "is_list_block": False})
        i += 1

    return props, blocks, body


def write_frontmatter(props: dict, blocks: list, body: str) -> str:
    written_keys = set()
    new_lines = []

    for block in blocks:
        key = block["key"]
        if key is None:
            new_lines.extend(block["lines"])
        else:
            if key in props:
                new_lines.append(f"{key}: {format_yaml_value(props[key])}")
                written_keys.add(key)

    for key, value in props.items():
        if key not in written_keys:
            new_lines.append(f"{key}: {format_yaml_value(value)}")

    if not new_lines and not body:
        return body
    return "---\n" + "\n".join(new_lines) + "\n---\n" + body


def update_props_in_file(
    path: Path,
    set_props=None,
    remove_keys=None,
    overwrite: bool = False,
) -> str:
    try:
        text = read_text_file(path)
        props, blocks, body = read_frontmatter(text)
        changed = False

        for key in remove_keys or []:
            if key in props:
                del props[key]
                changed = True

        for key, value in (set_props or {}).items():
            if value == "":
                continue
            if overwrite or key not in props or props[key] == "":
                if props.get(key) != value:
                    props[key] = value
                    changed = True

        if not changed:
            return "skipped"

        backup_file(path)
        path.write_text(write_frontmatter(props, blocks, body), encoding="utf-8")
        return "ok"
    except Exception as exc:
        return f"error:{exc}"


def apply_props_to_file(path: Path, new_props: dict, overwrite: bool = False) -> str:
    return update_props_in_file(path, set_props=new_props, overwrite=overwrite)


def remove_props_from_file(path: Path, keys: list) -> str:
    return update_props_in_file(path, remove_keys=keys)


def restore_backup(path: Path) -> str:
    bak_dir = path.parent / "_PKM_BACKUP"
    if not bak_dir.exists():
        return "no_backup"
    baks = sorted(bak_dir.glob(f"{path.stem}_*{path.suffix}.bak"))
    if not baks:
        return "no_backup"
    latest = baks[-1]
    shutil.copy2(latest, path)
    return f"restored:{latest.name}"


def get_current_props(path: Path) -> dict:
    try:
        text = read_text_file(path)
        props, _, _ = read_frontmatter(text)
        return props
    except Exception:
        return {}


def match_index(stem: str) -> dict:
    stem_lower = stem.lower()
    for key, value in INDEX_MAPPING.items():
        if key.lower() == stem_lower:
            return value
    for key, value in INDEX_MAPPING.items():
        if key.lower() in stem_lower or stem_lower in key.lower():
            return value
    return {}


def search_in_content(files: list, query: str) -> list:
    query_lower = query.lower()
    result = []
    for file_path in files:
        try:
            text = read_text_file(file_path).lower()
            if query_lower in text:
                result.append(file_path)
        except Exception:
            pass
    return result


def parse_obsidian_paths(text: str, vault_path: Path) -> tuple[list, list]:
    found = []
    not_found = []
    for raw_line in text.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = line.replace("\\", "/")
        if not line.endswith(".md"):
            line += ".md"
        candidate = vault_path / line
        if candidate.exists():
            found.append(candidate)
        else:
            stem = Path(line).stem
            matches = [file_path for file_path in vault_path.rglob("*.md") if file_path.stem == stem]
            if len(matches) == 1:
                found.append(matches[0])
            elif len(matches) > 1:
                best = min(matches, key=lambda file_path: len(str(file_path)))
                found.append(best)
            else:
                not_found.append(raw_line)
    return found, not_found
