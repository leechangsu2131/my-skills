"""Orchestrator — end-to-end PKM note organization pipeline.

Chains:  md_merger → NotebookLM (MCP) → parse → validate → apply

Modes:
  merge     — 번들 파일 생성만
  analyze   — NotebookLM MCP 호출 + 응답 파싱
  apply     — 추천 CSV를 Vault에 반영
  full      — merge → analyze → apply 전체 실행
  prompt    — 프롬프트 출력 (수동 사용)

Usage:
  python orchestrator.py merge  "<볼트 경로>" 
  python orchestrator.py full   "<볼트 경로>" --notebook-url <URL>
  python orchestrator.py apply  "<볼트 경로>" recommendations.csv --dry-run
  python orchestrator.py prompt --tier full
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(next(p / "_shared" for p in Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir  # 결과물(노트 내용 포함)은 저장소 밖 <내 문서>\my-skills-data 에 둔다
DEFAULT_BUNDLES_DIR = data_dir() / "notebooklm_bundle"
DEFAULT_REPORT_DIR = Path.home() / "Documents" / "backupvault" / "reports"


def run_merge(
    vault_path: Path,
    output_dir: Path,
    *,
    target: int = 299,
    replace: bool = True,
    flatten: bool = True,
) -> int:
    """Run md_merger.py to create bundles."""
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "md_merger.py"),
        str(vault_path),
        str(output_dir),
        "--target", str(target),
        "--mode", "toc",
        "--similarity-engine", "hybrid",
        "--flatten-output",
        "--inject-path-frontmatter",
    ]
    if replace:
        cmd.append("--replace-output")

    print(f"\n{'='*60}")
    print(f"[1/3] 번들 생성: {vault_path} → {output_dir}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, cwd=str(SCRIPT_DIR))
    return result.returncode


def run_analyze_manual(
    bundles_dir: Path,
    tier: str = "full",
) -> Path:
    """Print prompt and instructions for manual NotebookLM analysis.

    Returns the expected output path for the response file.
    """
    from notebooklm_prompts import select_prompt

    print(f"\n{'='*60}")
    print(f"[2/3] NotebookLM 분석 (수동)")
    print(f"{'='*60}")
    print()
    print("──── 아래 프롬프트를 NotebookLM에 입력하세요 ────")
    print()
    print(select_prompt(tier))
    print()
    print("──── 프롬프트 끝 ────")
    print()

    bundle_files = sorted(bundles_dir.glob("*.md"))
    bundle_files = [f for f in bundle_files if f.name != "_merge_report.md"]
    print(f"번들 파일 {len(bundle_files)}개:")
    for bf in bundle_files[:10]:
        print(f"  - {bf.name}")
    if len(bundle_files) > 10:
        print(f"  ... 외 {len(bundle_files) - 10}개")
    print()

    # Expected response file
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    response_path = bundles_dir / f"notebooklm_response_{ts}.md"
    print(f"NotebookLM 응답을 아래 파일에 저장하세요:")
    print(f"  {response_path}")
    print()
    print("저장 후 다음 명령으로 파싱 + 적용:")
    print(f'  python orchestrator.py apply "<vault_path>" "{response_path}" --dry-run')

    return response_path


def run_analyze_mcp(
    bundles_dir: Path,
    notebook_url: str | None = None,
    notebook_id: str | None = None,
    tier: str = "full",
) -> Path | None:
    """Run analysis via NotebookLM MCP.

    Note: This function is designed to be called by an AI agent
    (Antigravity/Claude) that has access to MCP tools.
    When run standalone, it falls back to manual mode.
    """
    print(f"\n{'='*60}")
    print(f"[2/3] NotebookLM MCP 분석")
    print(f"{'='*60}")

    # Check if we're in an MCP-capable environment
    # If not, fall back to manual
    try:
        from notebooklm_analyzer import call_notebooklm_mcp
        # This will raise NotImplementedError in standalone mode
        call_notebooklm_mcp("test", notebook_url=notebook_url)
    except (NotImplementedError, ImportError):
        print("MCP 환경이 아닙니다. 수동 모드로 전환합니다.")
        return run_analyze_manual(bundles_dir, tier)

    return None  # MCP mode would return the response path


def run_parse(response_file: Path, tier: str = "full") -> Path:
    """Parse NotebookLM response and generate CSV."""
    from notebooklm_analyzer import parse_and_validate, write_csv, write_validation_report

    print(f"\n{'='*60}")
    print(f"[2.5/3] 응답 파싱: {response_file}")
    print(f"{'='*60}")

    text = response_file.read_text(encoding="utf-8")
    parsed = parse_and_validate(text)

    csv_path = response_file.with_suffix(".csv")
    written = write_csv(parsed, csv_path, tier=tier)

    report_path = csv_path.with_name(csv_path.stem + "_validation.md")
    valid, issues = write_validation_report(parsed, report_path)

    print(f"  파싱: {len(parsed)}행")
    print(f"  CSV:  {csv_path} ({written}행)")
    print(f"  검증: 통과 {valid} / 문제 {issues}")
    print(f"  리포트: {report_path}")

    return csv_path


def run_apply(
    vault_path: Path,
    csv_path: Path,
    *,
    dry_run: bool = False,
    min_confidence: str = "중",
) -> int:
    """Run apply_gemini_recommendations.py."""
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "apply_gemini_recommendations.py"),
        str(vault_path),
        str(csv_path),
        "--min-confidence", min_confidence,
    ]
    if dry_run:
        cmd.append("--dry-run")

    print(f"\n{'='*60}")
    print(f"[3/3] Vault 반영 {'(미리보기)' if dry_run else '(실행)'}: {csv_path}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, cwd=str(SCRIPT_DIR))
    return result.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PKM 노트 정리 오케스트레이터",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # merge
    p_merge = sub.add_parser("merge", help="번들 파일 생성")
    p_merge.add_argument("vault", help="Obsidian Vault 경로")
    p_merge.add_argument("--output", default=None, help="번들 출력 경로")
    p_merge.add_argument("--target", type=int, default=299, help="목표 파일 수")

    # analyze
    p_analyze = sub.add_parser("analyze", help="NotebookLM 분석 (수동/MCP)")
    p_analyze.add_argument("--bundles-dir", default=None, help="번들 디렉토리")
    p_analyze.add_argument("--notebook-url", default=None, help="NotebookLM 공유 URL")
    p_analyze.add_argument("--notebook-id", default=None, help="NotebookLM 노트북 ID")
    p_analyze.add_argument(
        "--tier", choices=["full", "title", "links"], default="full"
    )

    # parse
    p_parse = sub.add_parser("parse", help="NotebookLM 응답 파싱")
    p_parse.add_argument("response_file", help="응답 파일 경로")
    p_parse.add_argument(
        "--tier", choices=["full", "title", "links"], default="full"
    )

    # apply
    p_apply = sub.add_parser("apply", help="추천 CSV를 Vault에 반영")
    p_apply.add_argument("vault", help="Obsidian Vault 경로")
    p_apply.add_argument("csv_file", help="추천 CSV 파일")
    p_apply.add_argument("--dry-run", action="store_true", help="미리보기만")
    p_apply.add_argument(
        "--min-confidence",
        choices=["상", "중", "하"],
        default="중",
        help="최소 확신도 (기본: 중)",
    )

    # full
    p_full = sub.add_parser("full", help="전체 파이프라인: merge → analyze → apply")
    p_full.add_argument("vault", help="Obsidian Vault 경로")
    p_full.add_argument("--output", default=None, help="번들 출력 경로")
    p_full.add_argument("--notebook-url", default=None, help="NotebookLM URL")
    p_full.add_argument("--notebook-id", default=None, help="NotebookLM 노트북 ID")
    p_full.add_argument("--target", type=int, default=299, help="목표 파일 수")
    p_full.add_argument(
        "--tier", choices=["full", "title", "links"], default="full"
    )
    p_full.add_argument("--dry-run", action="store_true", help="Vault 반영 미리보기")
    p_full.add_argument(
        "--min-confidence",
        choices=["상", "중", "하"],
        default="중",
    )

    # prompt
    p_prompt = sub.add_parser("prompt", help="프롬프트 출력")
    p_prompt.add_argument(
        "--tier", choices=["full", "title", "links"], default="full"
    )

    # batch-prompt
    p_batch = sub.add_parser("batch-prompt", help="배치 프롬프트 생성 (30개씩)")
    p_batch.add_argument("vault", help="Obsidian Vault 경로")
    p_batch.add_argument("--size", type=int, default=30, help="배치 크기 (기본: 30)")
    p_batch.add_argument("--bundles-dir", default=None, help="번들 디렉토리")
    p_batch.add_argument("--copy", action="store_true", help="클립보드에 복사")
    p_batch.add_argument(
        "--tier", choices=["full", "title", "links"], default="full"
    )

    return parser


def extract_source_paths_from_bundles(bundles_dir: Path) -> list[str]:
    """번들 파일들에서 모든 `원본 파일:` 경로를 추출한다."""
    import re
    paths = []
    skip_names = {"_merge_report.md", "llm-wiki 규칙.md", "template.md"}
    for bundle in sorted(bundles_dir.glob("*.md")):
        if bundle.name in skip_names:
            continue
        text = bundle.read_text(encoding="utf-8")
        for m in re.finditer(r"^>\s*원본 파일:\s*`([^`]+)`", text, re.MULTILINE):
            paths.append(m.group(1).strip())
    return paths


def load_processed_sources(state_path: Path) -> set[str]:
    """state.json에서 이미 처리된 source_path 목록을 가져온다."""
    import json
    if not state_path.exists():
        return set()
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        entries = state.get("entries", {})
        return {
            sp for sp, entry in entries.items()
            if entry.get("status") in ("applied", "absorbed", "planned")
        }
    except Exception:
        return set()


def run_batch_prompt(
    vault_path: Path,
    bundles_dir: Path,
    batch_size: int,
    tier: str,
    copy_to_clipboard: bool,
) -> int:
    """배치 프롬프트를 생성한다.

    모든 파일은 이미 NotebookLM에 업로드된 상태이므로,
    출력 범위만 제한하고 연결 후보는 전체 문서에서 탐색하도록 지시한다.
    """
    from notebooklm_prompts import select_prompt
    from pkm_core import read_frontmatter

    state_path = DEFAULT_REPORT_DIR / "gemini-applied" / "state.json"
    all_sources = extract_source_paths_from_bundles(bundles_dir)
    processed = load_processed_sources(state_path)

    remaining = [s for s in all_sources if s not in processed]

    print(f"전체 노트: {len(all_sources)}개")
    print(f"처리 완료: {len(processed)}개")
    print(f"남은 노트 총합: {len(remaining)}개")

    if not remaining:
        print("\n✅ 모든 노트가 처리되었습니다!")
        return 0

    prioritized_remaining = []
    secondary_remaining = []

    for src in remaining:
        note_p = vault_path / src
        is_priority1 = False
        lower_src = src.lower()
        if lower_src.startswith("00_inbox") or lower_src.startswith("2 area") or lower_src.startswith("3 resources"):
            is_priority1 = True
        else:
            if note_p.exists():
                text = note_p.read_text(encoding="utf-8")
                props, _, _ = read_frontmatter(text)
                if not props.get("domain") or not props.get("engine"):
                    is_priority1 = True
            else:
                is_priority1 = True
                
        if is_priority1:
            prioritized_remaining.append(src)
        else:
            secondary_remaining.append(src)

    if prioritized_remaining:
        batch = prioritized_remaining[:batch_size]
        print(f"\n[🔴 1순위 타겟] 미정리(레거시 폴더/속성없음) 노트 - 남은 {len(prioritized_remaining)}개 중 {len(batch)}개 선택")
    else:
        batch = secondary_remaining[:batch_size]
        print(f"\n[🟢 2순위 타겟] 이미 1차 정리된 노트 (사후 교정용) - 남은 {len(secondary_remaining)}개 중 {len(batch)}개 선택")

    batch_num = (len(processed) // batch_size) + 1
    total_batches = -(-len(all_sources) // batch_size)  # ceil division

    print(f"\n── 배치 {batch_num}/{total_batches} ({len(batch)}개) ──\n")

    # 기본 프롬프트 가져오기
    base_prompt = select_prompt(tier)

    # 파일 목록 블록 생성
    file_list = "\n".join(f"  {i+1}. `{s}`" for i, s in enumerate(batch))
    batch_instruction = f"""
추가 지시사항 (가장 중요함):
이번에는 아래 목록의 **정확히 {len(batch)}개 노트만** 분석하여 표로 출력하라.
목록에 없는 노트는 이번 응답에서 절대 분석하지 마라.
단, '연결 후보'를 찾을 때는 업로드된 **전체 문서**를 참조하여 적극적으로 탐색하라.

분석 대상 목록:
{file_list}
"""

    full_prompt = base_prompt.rstrip() + "\n" + batch_instruction

    print(full_prompt)

    if copy_to_clipboard:
        try:
            import subprocess
            process = subprocess.Popen(
                ["clip"], stdin=subprocess.PIPE, shell=True
            )
            process.communicate(full_prompt.encode("utf-16le"))
            print("\n📋 클립보드에 복사되었습니다!")
        except Exception as e:
            print(f"\n⚠️ 클립보드 복사 실패: {e}")

    print(f"\n── 다음 단계 ──")
    print(f"1. 위 프롬프트를 NotebookLM에 붙여넣기")
    print(f"2. 응답 표를 response.md에 저장")
    print(f'3. python orchestrator.py apply "<vault>" response.md')
    print(f"4. python orchestrator.py batch-prompt  (다음 배치)")

    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "batch-prompt":
        vault = Path(args.vault).resolve()
        bundles = Path(args.bundles_dir).resolve() if args.bundles_dir else DEFAULT_BUNDLES_DIR
        return run_batch_prompt(
            vault,
            bundles,
            batch_size=args.size,
            tier=args.tier,
            copy_to_clipboard=args.copy,
        )

    elif args.command == "merge":
        vault = Path(args.vault).resolve()
        output = Path(args.output).resolve() if args.output else DEFAULT_BUNDLES_DIR
        return run_merge(vault, output, target=args.target)

    elif args.command == "analyze":
        bundles = Path(args.bundles_dir).resolve() if args.bundles_dir else DEFAULT_BUNDLES_DIR
        if args.notebook_url or args.notebook_id:
            run_analyze_mcp(
                bundles,
                notebook_url=args.notebook_url,
                notebook_id=args.notebook_id,
                tier=args.tier,
            )
        else:
            run_analyze_manual(bundles, tier=args.tier)
        return 0

    elif args.command == "parse":
        response = Path(args.response_file).resolve()
        run_parse(response, tier=args.tier)
        return 0

    elif args.command == "apply":
        vault = Path(args.vault).resolve()
        csv_path = Path(args.csv_file).resolve()
        return run_apply(
            vault, csv_path,
            dry_run=args.dry_run,
            min_confidence=args.min_confidence,
        )

    elif args.command == "full":
        vault = Path(args.vault).resolve()
        output = Path(args.output).resolve() if args.output else DEFAULT_BUNDLES_DIR

        # Step 1: Merge
        rc = run_merge(vault, output, target=args.target)
        if rc != 0:
            print(f"\n번들 생성 실패 (코드 {rc})", file=sys.stderr)
            return rc

        # Step 2: Analyze
        if args.notebook_url or args.notebook_id:
            response_path = run_analyze_mcp(
                output,
                notebook_url=args.notebook_url,
                notebook_id=args.notebook_id,
                tier=args.tier,
            )
            if response_path is None:
                # Manual mode fallback — user needs to save response first
                return 0
        else:
            # Manual mode: print prompt and wait
            run_analyze_manual(output, tier=args.tier)
            print("\n응답 파일을 저장한 후 다음 명령으로 계속하세요:")
            print(f'  python orchestrator.py parse <response_file>')
            print(f'  python orchestrator.py apply "{vault}" <csv_file> --dry-run')
            return 0

        # Step 2.5: Parse response
        csv_path = run_parse(response_path, tier=args.tier)

        # Step 3: Apply
        return run_apply(
            vault, csv_path,
            dry_run=args.dry_run,
            min_confidence=args.min_confidence,
        )

    elif args.command == "prompt":
        from notebooklm_prompts import select_prompt
        print(select_prompt(args.tier))
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
