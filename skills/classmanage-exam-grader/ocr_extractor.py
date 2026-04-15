#!/usr/bin/env python3
"""
ocr_extractor.py - Gemini CLI를 사용하여 학생 시험지 PDF에서 답안을 추출합니다.

Gemini의 네이티브 멀티모달 기능을 활용하여 PDF를 직접 분석합니다.
별도 OCR 라이브러리 없이 Gemini CLI의 `-p` (비대화) 모드로 구조화된 JSON을 반환받습니다.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

SKILL_DIR = Path(__file__).parent
PROMPT_PATH = SKILL_DIR / "prompts" / "ocr_student_exam.txt"
CONFIG_PATH = SKILL_DIR / "config.json"


def load_config() -> dict:
    """config.json 로드"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_prompt(prompt_path: Optional[Path] = None) -> str:
    """프롬프트 템플릿 로드"""
    path = prompt_path or PROMPT_PATH
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def extract_json_from_response(text: str) -> Optional[dict]:
    """Gemini CLI 응답에서 JSON을 추출합니다.

    응답에 ```json 블록이 있으면 그 안의 내용을,
    없으면 전체 텍스트를 JSON으로 파싱합니다.
    """
    # 먼저 ```json ... ``` 블록 찾기
    json_block = re.search(r"```json\s*\n(.*?)```", text, re.DOTALL)
    if json_block:
        try:
            return json.loads(json_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    # ``` ... ``` 블록 찾기 (언어 지정 없는 경우)
    code_block = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 전체 텍스트에서 JSON 객체 찾기
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def run_gemini_ocr(pdf_path: str, prompt: str, config: dict) -> dict:
    """Gemini CLI를 호출하여 PDF에서 답안을 추출합니다.

    Args:
        pdf_path: 학생 시험지 PDF 경로
        prompt: OCR 프롬프트 텍스트
        config: 설정 딕셔너리

    Returns:
        구조화된 답안 딕셔너리

    Raises:
        RuntimeError: Gemini CLI 호출 실패 시
        ValueError: JSON 파싱 실패 시
    """
    gemini_cli = config.get("gemini_cli_path", "gemini")
    model = config.get("gemini_model", "gemini-2.5-flash")

    # PDF 경로를 절대 경로로 변환
    abs_pdf = str(Path(pdf_path).resolve())

    # 프롬프트에 파일 참조를 포함
    full_prompt = f"{prompt}\n\n@{abs_pdf}"

    import os
    cmd_name = "gemini.cmd" if os.name == "nt" else "gemini"
    
    cmd = [
        cmd_name,
        "-p", full_prompt,
        "-m", model,
    ]

    print(f"  🔍 Gemini CLI OCR 실행 중: {Path(pdf_path).name}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"⏰ Gemini CLI 타임아웃 (120초): {pdf_path}")
    except FileNotFoundError:
        raise RuntimeError(
            f"❌ Gemini CLI를 찾을 수 없습니다. '{gemini_cli}'가 설치되어 있는지 확인하세요.\n"
            "   설치: npm install -g @google/gemini-cli"
        )

    if result.returncode != 0:
        raise RuntimeError(
            f"❌ Gemini CLI 오류 (exit code {result.returncode}):\n{result.stderr}"
        )

    # 응답에서 JSON 추출
    response_text = result.stdout.strip()
    parsed = extract_json_from_response(response_text)

    if parsed is None:
        raise ValueError(
            f"❌ JSON 파싱 실패. Gemini 응답:\n{response_text[:500]}"
        )

    return parsed


def extract_answers(pdf_path: str, prompt_path: Optional[str] = None) -> dict:
    """단일 학생 시험지에서 답안을 추출합니다.

    Args:
        pdf_path: 학생 시험지 PDF 경로
        prompt_path: 커스텀 프롬프트 경로 (없으면 기본 프롬프트)

    Returns:
        학생 답안 딕셔너리 (student_answers schema)
    """
    config = load_config()
    prompt = load_prompt(Path(prompt_path) if prompt_path else None)
    return run_gemini_ocr(pdf_path, prompt, config)


def extract_batch(input_dir: str, output_dir: str, prompt_path: Optional[str] = None) -> list[dict]:
    """폴더 내 모든 학생 시험지를 배치 처리합니다.

    Args:
        input_dir: 학생 시험지 PDF들이 있는 폴더
        output_dir: 추출 결과 JSON 저장 폴더
        prompt_path: 커스텀 프롬프트 경로

    Returns:
        추출 결과 리스트 (성공/실패 포함)
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(input_path.glob("*.pdf"))
    if not pdf_files:
        print(f"⚠️ PDF 파일이 없습니다: {input_dir}")
        return []

    print(f"\n📚 {len(pdf_files)}개 시험지 OCR 시작...\n")

    results = []
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] {pdf_file.name}")
        try:
            answers = extract_answers(str(pdf_file), prompt_path)

            # 결과 저장
            out_file = output_path / f"{pdf_file.stem}_answers.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(answers, f, ensure_ascii=False, indent=2)

            print(f"  ✅ 저장: {out_file.name}")
            results.append({
                "file": pdf_file.name,
                "status": "success",
                "student_name": answers.get("student_name", "알 수 없음"),
                "answer_count": len(answers.get("answers", [])),
                "output": str(out_file),
            })
        except Exception as e:
            print(f"  ❌ 실패: {e}")
            results.append({
                "file": pdf_file.name,
                "status": "error",
                "error": str(e),
            })

    # 요약
    success = sum(1 for r in results if r["status"] == "success")
    print(f"\n📊 완료: {success}/{len(results)} 성공")

    return results


# ----- CLI 진입점 -----

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Gemini CLI로 학생 시험지 OCR")
    parser.add_argument("pdf", nargs="?", help="단일 PDF 파일 경로")
    parser.add_argument("--batch", type=str, help="배치 처리할 폴더 경로")
    parser.add_argument("--output", type=str, help="결과 저장 폴더 (기본: data/extracted)")
    parser.add_argument("--prompt", type=str, help="커스텀 프롬프트 파일 경로")
    args = parser.parse_args()

    config = load_config()
    default_output = str(SKILL_DIR / config["paths"]["extracted"])

    if args.batch:
        output = args.output or default_output
        results = extract_batch(args.batch, output, args.prompt)
        # 배치 요약 저장
        summary_path = Path(output) / "_batch_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n📋 배치 요약: {summary_path}")
    elif args.pdf:
        result = extract_answers(args.pdf, args.prompt)
        output_dir = Path(args.output or default_output)
        output_dir.mkdir(parents=True, exist_ok=True)
        out_file = output_dir / f"{Path(args.pdf).stem}_answers.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 저장: {out_file}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
