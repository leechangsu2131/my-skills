import argparse
import sys
import os
import glob
import asyncio
import parse_gongmun
from edufine_report import save_report
import playwright_edufine

async def main_async():
    parser = argparse.ArgumentParser(description="에듀파인 기안 다중 처리 자동화 도구")
    parser.add_argument("target", help="파싱할 ODT 공문 파일 경로 또는 대상 폴더 경로")
    parser.add_argument("--dry-run", action="store_true", help="브라우저에서 폼 입력 없이 파싱 결과만 확인")
    parser.add_argument("--report", help="저장할 엑셀 리포트 파일명 (기본값: result/ 폴더에 자동 생성)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(" 에듀파인 단일 기안 자동화 봇 (Single Mode)")
    print("=" * 60)
    
    # 1. 대상 파일 목록 수집
    files_to_process = []
    is_empty_run = False
    if args.target == "NO_FILE":
        is_empty_run = True
    elif os.path.isfile(args.target):
        files_to_process.append(args.target)
    elif os.path.isdir(args.target):
        search_pattern = os.path.join(args.target, "*.odt")
        files_to_process = glob.glob(search_pattern)
        if not files_to_process:
            print(f"[안내] 디렉토리에 ODT 파일이 없습니다. 빈 기안 모드로 진행합니다.")
            is_empty_run = True
    else:
        print(f"[안내] 지정된 경로({args.target})를 찾을 수 없거나 파일이 없습니다. 빈 기안 모드로 진행합니다.")
        is_empty_run = True
        
    if not files_to_process and not is_empty_run:
        is_empty_run = True
        
    print(f"[안내] 선택된 ODT 파일을 처리합니다.\n")
    
    # 2. 파싱 진행
    parsed_items = []
    if is_empty_run:
        print("[안내] ODT 파일 없이 순수 네비게이션 모드로 실행합니다.")
        parsed_items.append({'_filepath': '수동 작성 모드', 'data': {'제목': '빈 기안 (수동 작성)'}})
    else:
        for file_path in files_to_process:
            print(f"[파싱 중] {os.path.basename(file_path)}")
            try:
                data = parse_gongmun.parse_odt(file_path)
                parsed_items.append({'_filepath': file_path, 'data': data})
            except Exception as e:
                print(f"  [파싱 오류] {e}")
                # 오류가 나도 네비게이션을 위해 더미 데이터로 추가
                parsed_items.append({'_filepath': file_path, 'data': {'제목': f'오류 발생 문서 ({os.path.basename(file_path)})'}, 'error': str(e)})

    # 3. 브라우저 자동화 일괄 처리
    results = await playwright_edufine.process_batch(parsed_items, dry_run=args.dry_run)
    
    # 4. 리포트 저장
    if results:
        try:
            report_path = save_report(results, args.report)
            print("=" * 60)
            print(f"[완료] 처리 결과 리포트(Excel)가 저장되었습니다:\n -> {os.path.abspath(report_path)}")
        except Exception as e:
            print(f"\n[오류] 리포트 저장 실패: {e}")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
