#!/usr/bin/env python3
"""
photo-organizer: 사진 폴더 정리 스크립트
- 각 폴더 안 사진의 EXIF 제작 날짜를 읽어 폴더명 뒤에 날짜 범위를 붙임
- 중복 사진(MD5 해시 동일) 제거 (괄호 사본 우선 제거)
- 의미 없는 자동 파일명 → 폴더명_날짜_일련번호 형식으로 변경
"""

import os
import re
import hashlib
import shutil
import argparse
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    print("Pillow가 필요합니다: pip install Pillow")
    raise

# ───────────────────────────────────────────
# 설정
# ───────────────────────────────────────────
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.tiff', '.tif', '.bmp', '.webp'}

# 의미 없는 자동 생성 파일명 패턴 (카카오톡, 카메라 등)
AUTO_FILENAME_PATTERNS = [
    # KakaoTalk_20261104_142120253.jpg 형식
    re.compile(r'^KakaoTalk_\d{8}_\d{9}', re.IGNORECASE),
    # IMG_20261104_142120.jpg 형식
    re.compile(r'^IMG_\d{8}_\d{6}', re.IGNORECASE),
    # DSC_1234.jpg 형식
    re.compile(r'^DSC[_-]?\d{4,}', re.IGNORECASE),
    # 20261104_142120.jpg 형식 (날짜만)
    re.compile(r'^\d{8}_\d{6}'),
    # Screenshot_2026... 형식
    re.compile(r'^Screenshot_\d{4}', re.IGNORECASE),
    # 2022~어쩌구 형식 (숫자로 시작하는 긴 이름)
    re.compile(r'^20\d{2}[_\-]\d{2}[_\-]\d{2}'),
]

# 이미 날짜가 붙은 폴더명 패턴 (뒤에 _YYYYMMDD 또는 _YYYY-MM-DD 등)
FOLDER_DATE_PATTERN = re.compile(
    r'[_\s~]\d{4}[\-\.]\d{2}[\-\.]\d{2}(?:[~\-]\d{4}[\-\.]\d{2}[\-\.]\d{2})?$'
)


# ───────────────────────────────────────────
# 헬퍼 함수
# ───────────────────────────────────────────
def get_exif_date(path: Path) -> datetime | None:
    """EXIF DateTimeOriginal(제작 날짜)을 반환. 없으면 None."""
    try:
        img = Image.open(path)
        exif_data = img._getexif()
        if not exif_data:
            return None
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'DateTimeOriginal':
                return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
        # DateTimeOriginal 없으면 DateTime 사용
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'DateTime':
                return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass
    return None


def get_filename_date(filename: str) -> datetime | None:
    """파일명에서 날짜 추출 (YYYYMMDD 패턴)."""
    m = re.search(r'(20\d{2})(\d{2})(\d{2})', filename)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return None


def get_photo_date(path: Path) -> datetime | None:
    """EXIF → 파일명 순서로 날짜 추출."""
    dt = get_exif_date(path)
    if dt:
        return dt
    return get_filename_date(path.name)


def md5_hash(path: Path) -> str:
    """파일 MD5 해시 반환."""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def is_auto_filename(name: str) -> bool:
    """의미 없는 자동 생성 파일명인지 확인."""
    stem = Path(name).stem
    return any(p.match(stem) for p in AUTO_FILENAME_PATTERNS)


def folder_already_has_date(folder_name: str) -> bool:
    """폴더명에 이미 날짜가 붙어있는지 확인."""
    return bool(FOLDER_DATE_PATTERN.search(folder_name))


def is_duplicate_copy(filename: str) -> bool:
    """'파일명 (1).jpg' 형식의 사본인지 확인."""
    return bool(re.search(r'\s*\(\d+\)\s*$', Path(filename).stem))


# ───────────────────────────────────────────
# 핵심 로직
# ───────────────────────────────────────────
def collect_folder_dates(folder: Path, dry_run: bool) -> tuple[datetime | None, datetime | None]:
    """폴더 내 모든 사진의 최소/최대 날짜 반환."""
    dates = []
    for f in folder.iterdir():
        if f.suffix.lower() in IMAGE_EXTENSIONS and f.is_file():
            dt = get_photo_date(f)
            if dt:
                dates.append(dt)
    if not dates:
        return None, None
    return min(dates), max(dates)


def remove_duplicates(folder: Path, dry_run: bool) -> tuple[int, set[Path]]:
    """중복 파일 제거. 사본('(1)' 형식)을 우선 삭제. (삭제 건수, 삭제 대상 경로 집합) 반환."""
    seen_hashes: dict[str, Path] = {}
    to_delete: list[Path] = []

    # 파일 목록 정렬: 사본이 아닌 원본을 먼저 처리
    files = sorted(
        [f for f in folder.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS and f.is_file()],
        key=lambda f: (is_duplicate_copy(f.name), f.name)
    )

    for f in files:
        h = md5_hash(f)
        if h in seen_hashes:
            to_delete.append(f)
            print(f"  🗑  중복 삭제: {f.name}  (원본: {seen_hashes[h].name})")
        else:
            seen_hashes[h] = f

    if not dry_run:
        for f in to_delete:
            f.unlink()

    return len(to_delete), set(to_delete)


def rename_photos(folder: Path, activity_name: str, dry_run: bool,
                  skip_paths: set[Path] | None = None, class_id: str = '') -> int:
    """자동 생성 파일명 → 활동명_날짜_[반]_순번 형식으로 변경. 변경 건수 반환."""
    skip_paths = skip_paths or set()
    files = sorted(
        [f for f in folder.iterdir()
         if f.suffix.lower() in IMAGE_EXTENSIONS and f.is_file() and f not in skip_paths],
        key=lambda f: (get_photo_date(f) or datetime.min, f.name)
    )

    idx = 1
    renamed = 0
    for f in files:
        if not is_auto_filename(f.name):
            continue  # 의미 있는 이름은 그대로 둠

        dt = get_photo_date(f)
        date_str = dt.strftime('%Y%m%d') if dt else '날짜미상'

        # class_id가 있으면 활동명_날짜_반_순번, 없으면 활동명_날짜_순번
        if class_id:
            new_name = f"{activity_name}_{date_str}_{class_id}_{idx:02d}{f.suffix.lower()}"
        else:
            new_name = f"{activity_name}_{date_str}_{idx:02d}{f.suffix.lower()}"
        new_path = folder / new_name

        # 충돌 방지
        while new_path.exists():
            idx += 1
            if class_id:
                new_name = f"{activity_name}_{date_str}_{class_id}_{idx:02d}{f.suffix.lower()}"
            else:
                new_name = f"{activity_name}_{date_str}_{idx:02d}{f.suffix.lower()}"
            new_path = folder / new_name

        print(f"  ✏  이름 변경: {f.name} → {new_name}")
        if not dry_run:
            f.rename(new_path)
        idx += 1
        renamed += 1

    return renamed


def rename_folder(folder: Path, min_date: datetime, max_date: datetime, dry_run: bool) -> Path:
    """폴더명 뒤에 날짜(범위) 추가. 새 폴더 경로 반환."""
    name = folder.name

    if folder_already_has_date(name):
        print(f"  ⏭  날짜 이미 있음, 건너뜀: {name}")
        return folder

    if min_date.date() == max_date.date():
        date_suffix = f" {min_date.strftime('%Y-%m-%d')}"
    else:
        date_suffix = f" {min_date.strftime('%Y-%m-%d')}~{max_date.strftime('%Y-%m-%d')}"

    new_name = name + date_suffix
    new_path = folder.parent / new_name

    if new_path.exists():
        print(f"  ⚠  이름 충돌, 건너뜀: {new_name}")
        return folder

    print(f"  📁 폴더 이름 변경: {name} → {new_name}")
    if not dry_run:
        folder.rename(new_path)
    return new_path


# ───────────────────────────────────────────
# 메인
# ───────────────────────────────────────────
def process_root(root: Path, dry_run: bool, skip_rename_files: bool, skip_rename_folder: bool, class_id: str = '3-2'):
    """Pictures 루트 폴더 아래 모든 활동 폴더 처리."""
    folders = sorted([d for d in root.iterdir() if d.is_dir()])

    total_deleted = 0
    total_renamed_files = 0
    total_renamed_folders = 0

    for folder in folders:
        # Screenshots 폴더는 건너뜀
        if folder.name.lower() == 'screenshots':
            continue

        # 이미지 파일이 있는 폴더만 처리
        images = [f for f in folder.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS and f.is_file()]
        if not images:
            continue

        print(f"\n📂 처리 중: {folder.name}  ({len(images)}장)")

        # 1. 중복 제거
        deleted, deleted_paths = remove_duplicates(folder, dry_run)
        total_deleted += deleted

        # 2. 사진 파일 이름 변경 (삭제 대상은 제외)
        if not skip_rename_files:
            activity_name = re.sub(r'\s+', '_', folder.name.strip())
            # 이미 날짜 붙은 폴더명은 날짜 제거 후 활동명만 사용
            activity_name = re.sub(r'[_\s~]\d{4}[\-\.]\d{2}[\-\.]\d{2}.*$', '', activity_name)
            renamed = rename_photos(folder, activity_name, dry_run, deleted_paths, class_id=class_id)
            total_renamed_files += renamed

        # 3. 폴더 이름에 날짜 추가
        if not skip_rename_folder:
            min_date, max_date = collect_folder_dates(folder, dry_run)
            if min_date and max_date:
                rename_folder(folder, min_date, max_date, dry_run)
                total_renamed_folders += 1
            else:
                print(f"  ⚠  날짜를 읽을 수 없어 폴더명 변경 건너뜀")

    print(f"\n{'='*50}")
    print(f"✅ 완료!")
    print(f"   중복 삭제: {total_deleted}개" + (" (dry-run)" if dry_run else ""))
    print(f"   파일명 변경: {total_renamed_files}개" + (" (dry-run)" if dry_run else ""))
    print(f"   폴더명 변경: {total_renamed_folders}개" + (" (dry-run)" if dry_run else ""))


def main():
    parser = argparse.ArgumentParser(
        description="사진 폴더 자동 정리: 중복 제거 + 날짜 태그 + 파일명 정리"
    )
    parser.add_argument(
        'root',
        nargs='?',
        default=r'C:\Users\user\Pictures',
        help='정리할 최상위 폴더 (기본값: C:\\Users\\user\\Pictures)'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='실제 변경 없이 미리보기만 출력'
    )
    parser.add_argument(
        '--skip-rename-files',
        action='store_true',
        help='파일 이름 변경 건너뜀'
    )
    parser.add_argument(
        '--skip-rename-folder',
        action='store_true',
        help='폴더 이름 변경 건너뜀'
    )
    parser.add_argument(
        '--folder', '-f',
        help='특정 폴더 하나만 처리 (예: 게임만들기)'
    )
    parser.add_argument(
        '--class-id', '-c',
        default='3-2',
        help='파일명 중간에 들어갈 학급 정보 (기본값: 3-2, 빈 문자열 전달 시 생략)'
    )

    args = parser.parse_args()
    root = Path(args.root)

    if not root.exists():
        print(f"❌ 경로를 찾을 수 없습니다: {root}")
        return

    if args.dry_run:
        print("🔍 DRY-RUN 모드 — 실제 파일은 변경되지 않습니다.\n")

    if args.folder:
        # 특정 폴더만 처리
        target = root / args.folder
        if not target.is_dir():
            print(f"❌ 폴더를 찾을 수 없습니다: {target}")
            return
        process_root_single(target, args.dry_run, args.skip_rename_files, args.skip_rename_folder, class_id=args.class_id)
    else:
        process_root(root, args.dry_run, args.skip_rename_files, args.skip_rename_folder, class_id=args.class_id)


def process_root_single(folder: Path, dry_run: bool, skip_rename_files: bool, skip_rename_folder: bool, class_id: str = '3-2'):
    """단일 폴더 처리."""
    images = [f for f in folder.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS and f.is_file()]
    print(f"\n📂 처리 중: {folder.name}  ({len(images)}장)")

    deleted, deleted_paths = remove_duplicates(folder, dry_run)

    if not skip_rename_files:
        activity_name = re.sub(r'\s+', '_', folder.name.strip())
        activity_name = re.sub(r'[_\s~]\d{4}[\-\.]\d{2}[\-\.]\d{2}.*$', '', activity_name)
        rename_photos(folder, activity_name, dry_run, deleted_paths, class_id=class_id)

    if not skip_rename_folder:
        min_date, max_date = collect_folder_dates(folder, dry_run)
        if min_date and max_date:
            rename_folder(folder, min_date, max_date, dry_run)
        else:
            print(f"  ⚠  날짜를 읽을 수 없어 폴더명 변경 건너뜀")

    print(f"\n{'='*50}")
    print(f"✅ 완료! 중복 삭제: {deleted}개" + (" (dry-run)" if dry_run else ""))


if __name__ == '__main__':
    main()
