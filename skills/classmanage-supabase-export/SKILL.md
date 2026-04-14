---
description: Download and separate Supabase classroom records into individual student Excel sheets (A-type normalized mapping)
---

# Supabase-to-Sheet Экспорт 스킬 (학생별 낱개 분리)

이 스킬은 Supabase (`class-manage` 테이블 등)에 저장된 통합 수업 기록 데이터를 불러와서, 기록된 다중 학생 배열(예: "천선율, 김동규, 강시우")을 자동으로 개별 분리(Explode)합니다. 

결과적으로, 각 학생별로 오직 본인의 이름만 들어간 **'낱개 형식의 데이터'가 각자의 개별 워크시트(Sheet)에 나뉘어 담긴 엑셀 파일(student_records.xlsx)을 자동 생성**해 줍니다. 

## 사전 준비
이 스킬은 같은 `my-skills` 저장소 내 `notion-to-supabase`의 `.env` 환경변수를 공유 및 활용합니다.
또한, 파이썬의 `pandas`와 `openpyxl` 라이브러리가 필요합니다.

```bash
pip install pandas openpyxl requests python-dotenv
```

## 사용법 (Usage)

터미널에서 아래 명령어를 실행하여 엑셀 추출을 수행합니다.

```bash
python export.py
```

실행이 완료되면 현재 폴더 내에 `student_records.xlsx` 파일이 생성됩니다.
엑셀 파일을 열어보면 아래쪽에 학생 이름으로 된 수많은 탭(시트)들이 생성되어 있으며, 각 시트에는 해당 학생이 관여된 기록들만 완벽하게 필터링 및 1:1 대응 분리되어 저장되어 있습니다.
