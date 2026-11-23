"""
pkm_batch_apply.py
==================
재사용 가능한 PKM 노트 일괄 적용 도구.

사용법:
  python -X utf8 pkm_batch_apply.py <spec.yaml>            # 실행
  python -X utf8 pkm_batch_apply.py <spec.yaml> --dry-run  # 미리보기

충돌 감지 방식 (시간 기반 아님):
  배치 적용 시 각 노트의 내용 해시를 .pkm_batch_state.json에 저장한다.
  다음 배치 실행 시, 현재 파일 해시 vs 저장된 해시를 비교:
    - 같으면 → 사용자가 수정 안 함 → 안전하게 덮어씀
    - 다르면 → 사용자가 직접 수정함 → SKIPPED_USER_EDIT (건너뜀)

  spec에 body가 없으면 frontmatter만 업데이트하고 본문은 건드리지 않는다.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from pkm_core import (
    backup_file,
    read_frontmatter,
    update_links_for_note_change,
    write_frontmatter,
)

sys.path.insert(0, str(next(p / "_shared" for p in Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir, load_env  # 결과물(노트 내용 포함)은 저장소 밖 <내 문서>\my-skills-data 에 둔다

# 상태 파일 위치 (<내 문서>\my-skills-data\personal-obsidansystem-main)
STATE_FILE = data_dir() / ".pkm_batch_state.json"
READ_ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")

EXCLUDED_PARTS = {"_PKM_BACKUP", ".trash", ".obsidian", ".smart-env", "reports"}


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def read_safe(path: Path) -> str:
    for enc in READ_ENCODINGS:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def content_hash(text: str) -> str:
    """텍스트 내용의 SHA-1 해시 (공백 정규화)."""
    normalized = " ".join(text.split())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


# ── 상태 파일 ─────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── 노트 탐색 ─────────────────────────────────────────────────────────────────

def find_note(vault: Path, stem: str) -> Optional[Path]:
    """볼트에서 파일명(stem)으로 노트를 찾는다. 백업/숨김 폴더 제외."""
    candidates = [
        p for p in vault.rglob(f"{stem}.md")
        if not any(part in EXCLUDED_PARTS for part in p.parts)
    ]
    return candidates[0] if candidates else None


# ── frontmatter 병합 ──────────────────────────────────────────────────────────

def merge_frontmatter(props: dict, new_fm: dict) -> tuple[dict, list[str]]:
    """props에 new_fm을 병합. 변경된 키 목록 반환."""
    changed = []
    for key, val in new_fm.items():
        if props.get(key) != val:
            props[key] = val
            changed.append(key)
    return props, changed


# ── obsidian CLI 이동 ─────────────────────────────────────────────────────────

def run_obsidian_move(src_rel: str, dest_rel: str) -> Optional[bool]:
    """
    obsidian CLI로 파일을 이동 (내부 링크 자동 업데이트).
    반환값: True=성공, False=CLI 오류, None=CLI 미설치
    """
    cmd = ["obsidian", f"path={src_rel}", f"to={dest_rel}", "move"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            return True
        print(f"  [CLI 오류] {res.stderr.strip()}")
        return False
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        print("  [CLI 타임아웃]")
        return None


# ── 단일 노트 적용 ────────────────────────────────────────────────────────────

def apply_note(
    vault: Path,
    spec: dict,
    state: dict,
    dry_run: bool,
) -> dict:
    """
    단일 노트 스펙을 적용.
    state: 로드된 상태 dict (in-place 업데이트됨)
    반환: {stem, status, path, message}
    """
    stem = spec["stem"]
    old_stem = spec.get("old_stem", stem)   # 기존 파일명 (이름 변경 시 지정)
    absorb = spec.get("absorb", [])          # 병합 후 삭제할 추가 stem 목록
    target_folder = spec.get("target_folder", "")
    new_fm: dict = spec.get("frontmatter", {})
    new_body: Optional[str] = spec.get("body", None)
    append_body: Optional[str] = spec.get("append_body", None)
    append_links: list = spec.get("append_links", [])

    result = {"stem": stem, "status": "?", "path": None, "message": ""}

    # ── -1. 안전 검사: 옵시디언 링크 불가 특수문자 검열 ───────────────────────
    invalid_chars = set('<>:"/\\|?*#^[]')
    if any(char in invalid_chars for char in stem):
        result.update(status="ERROR_INVALID_FILENAME", 
                      message="파일명에 링크를 깨뜨리는 특수문자(# ^ [ ] | : 등)가 포함되어 있습니다. 명세서를 수정하세요.")
        return result

    # ── 0. 안전 검사: 병합 시 본문 누락 방지 ──────────────────────────────
    if absorb and new_body is None:
        result.update(status="ERROR_MERGE_NO_BODY", 
                      message="병합(absorb) 대상이 있지만 본문(body)이 제공되지 않아 데이터 유실 위험이 있습니다. 건너뜁니다.")
        return result

    # ── 1. 파일 탐색 (old_stem 우선) ──────────────────────────────────────────
    src = find_note(vault, old_stem) or find_note(vault, stem)

    if src is None:
        # 볼트에 없음 → 새로 생성
        if not target_folder:
            result["status"] = "NOT_FOUND"
            result["message"] = "볼트에서 찾을 수 없음 (target_folder 지정 시 새로 생성)"
            return result

        dest_dir = vault / target_folder
        dest = dest_dir / f"{stem}.md"

        if dry_run:
            msg = f"새로 생성 예정 → {target_folder}"
            if stem != old_stem:
                msg = f"⚠️ [경고] 기존 파일 '{old_stem}'을 찾을 수 없어 새로 생성됩니다! → {target_folder}"
            result.update(status="DRY_CREATE", path=str(dest.relative_to(vault)), message=msg)
            return result

        dest_dir.mkdir(parents=True, exist_ok=True)
        props = dict(new_fm)
        body = (new_body or "").strip() + "\n"
        if append_body:
            body = body.rstrip() + "\n\n" + append_body.strip() + "\n"
        if append_links:
            links_text = "\n\n#### 🔗 연결 노트\n" + "\n".join(f"* [[{str(c).strip(' []')}]]" for c in append_links if str(c).strip())
            body = body.rstrip() + links_text + "\n"
            
        text = write_frontmatter(props, [], body) if props else body
        dest.write_text(text, encoding="utf-8")
        state[stem] = content_hash(text)
        # absorb: 추가 흡수 파일 삭제
        for a_stem in absorb:
            a_path = find_note(vault, a_stem)
            if a_path:
                backup_file(a_path, vault)
                update_links_for_note_change(vault, a_path, dest)
                a_path.unlink()
                result["message"] += f" + 흡수:{a_stem}"

        result.update(status="CREATED", path=str(dest.relative_to(vault)),
                      message=f"새로 생성 → {target_folder}" + result["message"])
        return result

    result["path"] = str(src.relative_to(vault))

    # ── 2. 현재 파일 내용 읽기 ────────────────────────────────────────────────
    current_text = read_safe(src)
    current_hash = content_hash(current_text)

    # ── 3. 사용자 수정 감지 (해시 비교) ──────────────────────────────────────
    # body, append_body, append_links가 spec에 있을 때만 해시로 수정 여부를 판단한다.
    # 본문을 전혀 건드리지 않으면 frontmatter만 수정하므로 해시 충돌 검사 불필요.
    if new_body is not None or append_body is not None or append_links:
        stored_hash = state.get(stem)
        if stored_hash is not None and current_hash != stored_hash:
            result["status"] = "SKIPPED_USER_EDIT"
            result["message"] = (
                "사용자가 직접 수정한 파일 → 건너뜀 "
                "(강제 덮어쓰려면 state 파일에서 해당 항목 삭제)"
            )
            return result

    # ── 4. frontmatter 병합 ───────────────────────────────────────────────────
    props, blocks, body = read_frontmatter(current_text)
    props, changed_keys = merge_frontmatter(props, new_fm)

    # ── 5. 본문 교체 및 추가 ──────────────────────────────────────────────────────────
    body_changed = False
    if new_body is not None:
        new_body_norm = new_body.strip() + "\n"
        if body.strip() != new_body.strip():
            body = new_body_norm
            body_changed = True

    if append_body:
        body = body.rstrip() + "\n\n" + append_body.strip() + "\n"
        body_changed = True

    if append_links:
        links_text = "\n\n#### 🔗 연결 노트\n" + "\n".join(f"* [[{str(c).strip(' []')}]]" for c in append_links if str(c).strip())
        body = body.rstrip() + links_text + "\n"
        body_changed = True

    # ── 6. 이동/이름변경 필요 여부 ─────────────────────────────────────────────
    dest_dir = vault / target_folder if target_folder else src.parent
    dest = dest_dir / f"{stem}.md"    # 새 이름(이름변경 시 stem != src.stem)
    need_move = dest.resolve() != src.resolve()

    # ── 7. dry-run ────────────────────────────────────────────────────────────
    if dry_run:
        actions = []
        if changed_keys:
            actions.append(f"FM 업데이트: {changed_keys}")
        if body_changed:
            actions.append("본문 교체")
        if need_move:
            actions.append(f"이동: {src.relative_to(vault)} → {dest.relative_to(vault)}")
        if not actions:
            actions.append("변경 없음")
        result.update(status="DRY_RUN", message=" | ".join(actions))
        return result

    # ── 8. 변경 없으면 스킵 ───────────────────────────────────────────────────
    if not changed_keys and not body_changed and not need_move:
        result.update(status="SKIPPED", message="변경 사항 없음")
        return result

    # ── 9. 백업 ───────────────────────────────────────────────────────────────
    backup_file(src, vault)

    # ── 10. 새 내용 구성 ──────────────────────────────────────────────────────
    new_text = write_frontmatter(props, blocks, body)

    # ── 11. 이동 처리 ─────────────────────────────────────────────────────────
    if need_move:
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # 원본을 먼저 새 내용으로 업데이트
        src.write_text(new_text, encoding="utf-8")

        # CLI 이동 요청
        cli_ok = run_obsidian_move(
            src.relative_to(vault).as_posix(),
            dest.relative_to(vault).as_posix(),
        )
        
        import time
        time.sleep(0.5) # 옵시디언이 처리를 완료할 대기시간
        
        if cli_ok is True and dest.exists():
            # 옵시디언이 성공적으로 이동함 (백링크 자동 업데이트됨)
            result["status"] = "MOVED_CLI"
            if src.exists() and src.resolve() != dest.resolve():
                src.unlink() # 만약 남아있다면 삭제
        else:
            # 옵시디언 이동이 실패했거나 dest가 안 만들어진 경우 수동 처리
            dest.write_text(new_text, encoding="utf-8")
            if src.exists() and src.resolve() != dest.resolve():
                src.unlink()
            update_links_for_note_change(vault, src, dest)
            result["status"] = "MOVED_PY" if cli_ok is None else "MOVED_PY_FALLBACK"

        result["path"] = str(dest.relative_to(vault))
        result["message"] = f"{src.relative_to(vault)} → {dest.relative_to(vault)}"
        state[stem] = content_hash(new_text)
    else:
        src.write_text(new_text, encoding="utf-8")
        result.update(status="UPDATED",
                      message=f"FM:{changed_keys} 본문:{body_changed}")
        state[stem] = content_hash(new_text)

    # ── 12. absorb: 병합 후 추가 파일 삭제 ──────────────────────────────────────
    for a_stem in absorb:
        a_path = find_note(vault, a_stem)
        if a_path and a_path.resolve() != dest.resolve():
            backup_file(a_path, vault)
            update_links_for_note_change(vault, a_path, dest)
            a_path.unlink()
            result["message"] += f" + 흡수:{a_stem}"

    return result


# ── 메인 실행 ─────────────────────────────────────────────────────────────────

ICONS = {
    "CREATED": "[+]", "UPDATED": "[~]", "MOVED_CLI": "[>]", "MOVED_PY": "[>]",
    "MOVED_PY_FALLBACK": "[>]", "SKIPPED": "[ ]", "SKIPPED_USER_EDIT": "[!]",
    "NOT_FOUND": "[X]", "DRY_RUN": "[?]", "DRY_CREATE": "[?]",
}


def run(spec_path: Path, dry_run: bool) -> None:
    with open(spec_path, encoding="utf-8") as f:
        spec_data = yaml.safe_load(f)

    vault_raw = str(spec_data.get("vault") or "").strip()
    if not vault_raw or vault_raw.startswith("<"):
        # 프롬프트 예시는 실제 경로를 싣지 않으므로 중앙 .env 값으로 채운다
        load_env()
        vault_raw = os.environ.get("PERSONAL_OBSIDANSYSTEM_MAIN__VAULT", "")
    if not vault_raw:
        sys.exit("볼트 경로가 없습니다. YAML의 vault: 또는 중앙 .env의 PERSONAL_OBSIDANSYSTEM_MAIN__VAULT 를 채우세요.")
    vault = Path(vault_raw)
    notes = spec_data.get("notes", [])
    state = load_state()

    print(f"{'[DRY RUN] ' if dry_run else ''}볼트: {vault}")
    print(f"처리 노트 수: {len(notes)}")
    print(f"상태 파일: {STATE_FILE.name} ({len(state)}개 항목 기록됨)")
    print("-" * 60)

    stats: dict[str, int] = {}

    for note_spec in notes:
        result = apply_note(vault=vault, spec=note_spec, state=state, dry_run=dry_run)
        status = result["status"]
        stats[status] = stats.get(status, 0) + 1
        icon = ICONS.get(status, "[?]")
        print(f"{icon} [{status}] {result['stem']}")
        if result["message"]:
            print(f"     {result['message']}")

    if not dry_run:
        save_state(state)
        print(f"\n상태 저장: {STATE_FILE}")

    print("-" * 60)
    print("결과 요약:")
    for k, v in sorted(stats.items()):
        if v:
            print(f"  {k}: {v}")

    if stats.get("SKIPPED_USER_EDIT"):
        print(
            "\n[!] 사용자 수정 감지된 노트가 있습니다."
            "\n    강제로 덮어쓰려면 .pkm_batch_state.json에서 해당 stem 항목을 삭제하세요."
        )


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="PKM 노트 일괄 적용 도구 (해시 기반 충돌 감지)")
    parser.add_argument("spec", help="YAML 명세 파일 경로")
    parser.add_argument("--dry-run", action="store_true", help="미리보기 (실제 변경 없음)")
    args = parser.parse_args()
    run(Path(args.spec), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
