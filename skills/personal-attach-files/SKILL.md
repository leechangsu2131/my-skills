---
name: personal-attach-files
description: Gather distributed core code files into a single popup window for easy drag-and-drop attachment to frontier AI models (Claude, Gemini).
---

# 📂 personal-attach-files 스킬 가이드

이 스킬은 프로젝트 내 각지에 분산되어 있는 핵심 소스 코드 및 기획 파일들을 하나의 임시 폴더(`snapshot_to_ai/`)로 일괄 수집한 뒤, Windows 탐색기를 자동으로 팝업하여 프론티어 AI 모델(Claude, Gemini 등)에게 손쉽게 드래그 앤 드롭으로 파일 첨부를 마칠 수 있도록 돕는 커스텀 에이전트 스킬입니다.

---

## 🛠 작동 원리 및 스크립트 구조

1. **`gather_for_ai.ps1`**: 
   - 프로젝트 루트 디렉토리 대비 지정된 파일들(`SKILL.md`, `00001_initial_schema.sql`, `group_matching_page.dart` 등)을 식별 가능한 순서(`01_`, `02_` 등)로 복사합니다.
   - `snapshot_to_ai/` 폴더를 새로이 구성하고, 탐색기 프로세스(`explorer.exe`)를 실행하여 해당 폴더 창을 화면 전면에 띄웁니다.
2. **`gather.bat`**:
   - 일반 Windows 환경에서 권한 우회 옵션(`-ExecutionPolicy Bypass`)을 얹어 파워쉘 파일을 더블 클릭 한 번으로 가동해 주는 단축 래퍼(Wrapper) 스크립트입니다.

---

## 🚀 사용법 및 실행 명령

### 방법 1. 사용자가 직접 윈도우에서 실행 시
- [gather.bat](file:///C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-attach-files/scripts/gather.bat) 파일을 더블 클릭하여 기동합니다.
- 탐색기 창이 열리면 **`Ctrl + A`로 전체 파일을 선택**하고, 크롬 브라우저의 Claude/Gemini 입력창으로 **드래그 앤 드롭**하여 던집니다.

### 방법 2. 에이전트(Antigravity)에게 요청 시
- 사용자나 에이전트가 터미널에서 다음 명령어를 실행하여 팝업을 직접 트리거할 수 있습니다:
```powershell
# PowerShell CLI
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-attach-files\scripts\gather_for_ai.ps1"
```
```cmd
# cmd / batch
C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-attach-files\scripts\gather.bat
```

---

## 📋 기본 수집 대상 파일 리스트
- [SKILL.md](file:///c:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-free-parents-app/SKILL.md)
- [00001_initial_schema.sql](file:///c:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-free-parents-app/supabase/migrations/00001_initial_schema.sql)
- [group_matching_page.dart](file:///c:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-free-parents-app/lib/features/group/presentation/group_matching_page.dart)
- [login_page.dart](file:///c:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-free-parents-app/lib/features/auth/presentation/login_page.dart)
- [onboarding_page.dart](file:///c:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-free-parents-app/lib/features/home/presentation/onboarding_page.dart)
