---
name: admin-class-buy
description: "Help with Korean elementary school class operating fund work: K-에듀파인 학급운영비 개산급/개산급정산등록, receipt-by-receipt settlement row preparation, and creation of DOCX 증빙자료 pages from receipt and purchase item data. Use when Codex needs to support 담임교사 학급 자율 운영비 개산급 지급 후 정산, 증빙자료 서식 작성, or K-에듀파인 개산급정산등록 workflows."
---

# Admin Class Buy

Support the teacher-facing workflow for 학급 자율 운영비 paid as 개산급: prepare valid settlement rows, open K-에듀파인 개산급정산등록, and create 증빙자료 pages to submit with the printed settlement form.

## First Steps

1. Read `references/class_fund_rules.md` when checking whether an expense is allowed, how much can be spent, what evidence is needed, or what submission rules apply.
2. Read `references/edufine_workflow.md` before driving K-에듀파인.
3. Read `문제해결.md` before live K-에듀파인 execution and append any new failures and fixes after troubleshooting.
4. Ask for or infer these fields before creating output: 학년도, 학년, 반, 학생 수, 담임명, receipt date, vendor, amount, evidence type, activity category, usage detail, and item rows.
5. Never invent receipt contents from blurry images. If the receipt or item list is uncertain, show the extracted text and get user confirmation before writing files or entering K-에듀파인.

## Common Workflows

### Create 증빙자료 DOCX

Use `scripts/generate_evidence_docx.py` when the user needs the 서식의 증빙자료 page.

Input can be JSON or CSV. JSON supports multiple receipts and item rows:

```json
{
  "school_year": 2026,
  "grade": 3,
  "class_no": 2,
  "teacher": "홍길동",
  "receipts": [
    {
      "date": "2026-04-10",
      "vendor": "OO문구",
      "activity": "학생 개별 상담 활동",
      "usage": "생일선물(문구세트) 구입",
      "amount": 80000,
      "evidence_type": "전산자료",
      "items": [
        {"name": "문구세트", "quantity": 10, "amount": 80000}
      ]
    }
  ]
}
```

Run:

```bash
python scripts/generate_evidence_docx.py input.json --output 증빙자료.docx
```

### Register K-에듀파인 settlement rows

Use `scripts/edufine_class_settlement.py` only after the user has opened Chrome with remote debugging and logged in through 업무포털/NEIS.

Safe workflow:

1. Start Chrome using the same pattern as `admin-edufine/launch_chrome.bat` or any Chrome instance with `--remote-debugging-port=9222`.
2. Log in manually and open K-에듀파인.
3. Run the script in preview mode first:

```bash
python scripts/edufine_class_settlement.py rows.json --dry-run
```

4. Run without `--dry-run` to navigate to `학교회계 > 사업담당 > 품의/정산 > 개산급정산등록`, query from `2026-03-01`, and attempt row entry.
5. Stop before irreversible actions. The user should visually confirm rows, save, print, sign, and submit according to local practice.

If CDP is not available, run `scripts/launch_edufine_chrome.bat`, log in, and retry.

## Guardrails

- Enter only expenses paid after 개산급 지급; pre-payment expenses are not 정산 가능.
- Keep one settlement row per receipt. Use `행추가` for each receipt.
- Confirm the remaining/over-short amount before submission.
- Do not click final approval, irreversible submission, or 정산완료 buttons unless the user explicitly asks and is watching the session.
- For images or scanned receipts, prefer structured data from card statements, 거래명세표, 견적서, S2B output, or manually confirmed text.

## Useful Neighbor Skills

- Use `admin-edufine` patterns for Chrome CDP attachment and Nexacro-style frame/coordinate clicking.
- Use `admin-s2b-buyer` when S2B cart/견적자료 are needed before settlement.
- Use `admin-buying-product` extraction discipline when purchase lists come from online cart files or screenshots.
- Use `admin-neis-bot` frame-search patterns when a government site hides controls inside iframes or layered windows.
