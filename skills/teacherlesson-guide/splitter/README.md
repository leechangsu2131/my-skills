# 지도서 PDF 분할기

이 도구는 교사용 지도서 PDF에서 단원·차시의 시작과 끝을 찾아 작은 PDF 파일로 나눕니다. 목차, 차시별 지도 계획표, 단원 개관 쪽 등을 살펴 분할 범위를 정합니다.

상위 스킬의 전체 작업 순서(지도서 받기 → 나누기 → 진도표 행 만들기)는 [teacherlesson-guide/SKILL.md](../SKILL.md)를 참고하세요. 이 문서는 분할기 프로그램과 명령어 사용법을 설명합니다.

## 설치

일반 실행에 필요한 라이브러리를 설치합니다.

\`\`\`bash
pip install -r requirements.txt
\`\`\`

시험과 개발용 점검 도구까지 사용하려면 다음 파일도 설치합니다.

\`\`\`bash
pip install -r requirements-dev.txt
\`\`\`

## 화면에서 나누기

\`\`\`bash
python app.py
\`\`\`

1. 나눌 지도서 PDF를 고릅니다.
2. 결과를 저장할 폴더를 정합니다.
3. 분할 범위를 고릅니다.
   - **단원 단위만 분할**: 단원별로 나눕니다.
   - **차시/세부 제재까지 분할**: 차시나 세부 제재까지 더 작게 나눕니다.
4. 같은 이름의 결과 폴더가 이미 있을 때 처리 방법을 고릅니다.
   - 기존 폴더를 지우고 새로 만들기
   - (1)처럼 번호를 붙인 새 폴더 만들기
5. 이전 분석 결과를 다시 쓸지 정합니다. 기본값은 매번 PDF를 새로 분석하는 것입니다.
6. **미리보기**를 눌러 분할 범위와 제목을 확인합니다.
7. 확인이 끝나면 **분할 저장**을 누릅니다.

## 명령어로 나누기

먼저 결과만 살펴보려면 --dry-run을 사용합니다. 이때 분할 PDF는 저장하지 않습니다.

\`\`\`bash
python scripts/split_subunits_from_plan_table.py --pdf "teacher-guide.pdf" --out-dir "output" --dry-run
\`\`\`

확인한 뒤 실제 파일을 만들려면 --save를 사용합니다.

\`\`\`bash
python scripts/split_subunits_from_plan_table.py --pdf "teacher-guide.pdf" --out-dir "output" --save
\`\`\`

같은 이름의 결과 폴더가 이미 있을 때는 다음 중 하나를 고릅니다.

\`\`\`bash
# 기존 결과 폴더를 지우고 새로 만들기
python scripts/split_subunits_from_plan_table.py --pdf "teacher-guide.pdf" --out-dir "output" --save --existing-run-dir replace

# (1), (2)처럼 번호를 붙여 새 폴더에 저장하기
python scripts/split_subunits_from_plan_table.py --pdf "teacher-guide.pdf" --out-dir "output" --save --existing-run-dir suffix
\`\`\`

이전 구조 분석 결과를 다시 쓰려면 --use-cache를 지정합니다. 기본값은 새로 분석하는 것입니다.

\`\`\`bash
python scripts/split_subunits_from_plan_table.py --pdf "teacher-guide.pdf" --out-dir "output" --use-cache --dry-run
\`\`\`

차시나 세부 제재까지 더 자세히 나누려면 --split-level detail을 사용합니다.

\`\`\`bash
python scripts/split_subunits_from_plan_table.py --pdf "teacher-guide.pdf" --out-dir "output" --split-level detail --dry-run
\`\`\`

목차를 우선 기준으로 삼으려면 다음과 같이 실행합니다.

\`\`\`bash
python scripts/split_subunits_from_plan_table.py --pdf "teacher-guide.pdf" --out-dir "output" --strategy toc --dry-run
\`\`\`

## 주요 선택 항목

| 항목 | 설명 |
|---|---|
| --strategy | 분할 기준: auto(자동), toc(목차), plan(지도 계획표), overview(단원 개관) |
| --split-level | unit은 단원 단위, detail은 차시·세부 제재 단위로 나눕니다. |
| --scan-pages | 목차나 차시 계획표를 찾기 위해 앞쪽에서 살펴볼 쪽 수입니다. |
| --page-offset | 자동으로 맞춘 쪽 번호에 더하거나 뺄 값을 지정합니다. |
| --z-col | 지도 계획표에서 지도서 쪽 번호가 있는 열을 직접 지정합니다. |
| --existing-run-dir | 같은 이름의 결과 폴더 처리 방법: reuse, replace, suffix |
| --use-cache | output/.cache에 저장된 이전 구조 분석 결과를 다시 씁니다. |

PDF가 단원 페이지부터 바로 시작하고 '단원 개관', '제재 개관' 같은 제목으로 단원이 구분되어 있으면 --strategy overview가 도움이 됩니다.

목차나 지도 계획표에서 뽑은 제목이 잘렸거나 글자 인식이 어색하면, 분할 대상 쪽의 실제 제목을 참고해 해당 묶음의 제목을 보정합니다. 과목마다 예외 제목을 따로 추가하는 방식은 피합니다.

## 결과물

output 폴더 아래에 PDF 이름으로 된 결과 폴더가 만들어집니다.

- groups.json: 찾아낸 구간, 세부 묶음, 최종 분할 묶음, 사용한 분할 기준을 기록합니다.
- pdf_splits/: 단원·차시별로 나눈 PDF 파일을 저장합니다.

지도서 PDF와 분할 결과는 저작물이므로 공개 저장소에 올리지 말고, 교사 PC의 작업 폴더에 보관하세요.
