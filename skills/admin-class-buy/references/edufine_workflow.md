# K-에듀파인 개산급정산등록 워크플로우

## Preconditions

- Use Chrome remote debugging on port `9222`.
- The user must complete 업무포털/NEIS login manually and open K-에듀파인.
- Prefer attaching to an existing browser session over starting a fresh automated login.
- Do not store or ask for certificate passwords.

## Navigation

Teacher-side settlement path from the 안내 자료:

1. `사업관리`
2. `사업담당`
3. `품의/정산`
4. `개산급정산등록`
5. 시작일자 `2026-03-01` 입력
6. `조회`
7. Select the relevant 개산급 row
8. Add one settlement row per receipt
9. Save, then submit/print only after user confirmation

Admin-office reference path:

1. `지출관리`
2. `기타관리`
3. `개산급정산`
4. `개산급정산관리`

## Row Data Contract

Scripts and prompts should normalize receipt rows to:

```json
{
  "date": "2026-04-10",
  "vendor": "OO문구",
  "amount": 80000,
  "evidence_type": "전산자료",
  "usage": "생일선물(문구세트) 구입"
}
```

## Automation Notes

- K-에듀파인 is Nexacro-like; visible controls may be off-DOM or duplicated as accessibility nodes.
- Search all pages and frames. Click only visible elements with positive bounding boxes.
- If navigation fails, ask the user to manually open `개산급정산등록`; continue once the page is detected.
- Use keyboard entry as a fallback for grid cells: click row, press Enter, type, press Enter, then Tab to the next cell.
- Always print a preview table before live entry.
