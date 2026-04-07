---
name: hitalk-score-sender
description: Send individualized HiTalk messages from HiClass using a Google Sheet roster and a reusable text template. Use when working in HiTalk to send parents or students personalized messages such as score notices, learning-support invitations, counseling follow-ups, participation requests, or other small-batch classroom notices. This skill fits especially well when only a subset of students should receive a message and the wording should be previewed before sending.
---

# HiTalk Individual Sender

Use this skill when the user wants to send a custom HiTalk message to selected students or parents through HiClass.

The existing toolchain in this folder already supports:

- Reading recipients from Google Sheets through `gws`
- Reusing shared service-account credentials from nearby teacher tools when available
- Previewing messages with `--dry-run`
- Safe input rehearsal with `--rehearsal`
- Real sending through Selenium after the user logs into HiTalk
- Reusing long message templates from `.txt` files
- Filling placeholders not only for score fields, but also for arbitrary sheet headers such as `[담임교사]`, `[평가명]`, `[역할명]`
- Filtering recipients by a marker column such as `보충지도=y`

## Prefer This Workflow

1. Confirm the recipient set first.
If the user says "몇몇 학생" or "일부 학생", narrow `config.json` `range` to just those rows, or ask the user to prepare a small dedicated sheet/range.

2. Put long text into a template file.
For long parent messages, prefer a `.txt` template file in this folder over a one-line CLI string.

3. Preview before sending.
Run `python hitalk_sender.py --dry-run` first and inspect `preview.txt`.

4. Rehearse before real delivery.
Run `python hitalk_sender.py --rehearsal` to verify search, chat focus, and input clearing without sending.

5. Send only after the preview wording is approved.

## Main Files

- `hitalk_sender.py`: CLI sender
- `hitalk_sender_gui.py`: GUI wrapper
- `config.json`: sheet/range/message defaults
- `custom_message_template.txt`: basic score-message example
- `learning_guidance_invitation_template.txt`: example for 학습지도 권유/보충프로그램 안내

## Sheet Setup

At minimum, the sheet needs a student name column.

Typical examples:

- Score notice: `번호 | 이름 | 점수`
- Learning-support invitation: `이름 | 담임교사 | 평가명 | 역할명`
- Rich custom message: `이름 | 점수 | 담임교사 | 평가명 | 역할명 | 강조점`

Notes:

- `name_column` should point to the student-name column.
- `score_column` can stay as-is if score exists, but messages can still work even when a row has no score.
- Any additional header can be used directly in the template as `[헤더명]`.
- If you only want some students, set `recipient_filter_column` and optionally `recipient_filter_values`.
- Example: `recipient_filter_column = "보충지도"` and `recipient_filter_values = "y"` sends only rows marked with `y`.
- If `recipient_filter_values` is left blank, any non-empty value in that column is treated as selected.

## Template Placeholders

Built-in placeholders:

- `[학생]`, `{student_name}`, `{name}`
- `[과목]`, `{subject}`
- `[점수]`, `{score}`
- `[코멘트]`, `{comment}`
- Korean particles are auto-resolved for patterns like `[학생]이/가`, `[학생]은/는`, `[학생]는/이는`, `[학생]을/를`, `[학생]과/와`, `[학생]으로/로`

Sheet-header placeholders:

- If the sheet header is `담임교사`, use `[담임교사]` or `{담임교사}`
- If the sheet header is `역할명`, use `[역할명]` or `{역할명}`
- Headers are also exposed as normalized snake_case keys, so `또래 교사 역할` can also be used as `{또래_교사_역할}`

## Recommended Commands

```powershell
python hitalk_sender_gui.py
python hitalk_sender.py --dry-run
python hitalk_sender.py --message-file learning_guidance_invitation_template.txt --dry-run
python hitalk_sender.py --rehearsal
python hitalk_sender.py
```

## gws Authentication

This skill reads Google Sheets through `gws`, so even read-only preview requires Google authentication.

Recommended setup:

1. Install `gws`
```powershell
npm install -g @googleworkspace/cli
```

2. Create or download a Desktop OAuth client JSON from Google Cloud Console

3. Save it as:
`C:\Users\user\.config\gws\client_secret.json`

4. Run:
```powershell
gws auth login
```

`gws auth setup` is optional convenience automation. It needs `gcloud` installed, so manual `client_secret.json` setup is often simpler on Windows.

## Agent Guidance

When the user provides message text directly:

1. Save it into a descriptive template file in this folder.
2. Keep the user wording unless they ask for a rewrite.
3. Replace only obviously reusable parts with placeholders such as `[학생]`, `[담임교사]`, `[평가명]`.
4. Use dry-run output to show the filled preview before any send step.

When the user asks for score messages, use the existing score-based setup.

When the user asks for 학습지도 권유, 보충프로그램 안내, 상담 안내, 또래교사 역할 안내, or similar parent communication, prefer a custom template file and lean on header placeholders rather than rewriting the automation.

## Safety Checks

- Make sure only one HiTalk tab is open.
- Do not skip `--dry-run`.
- Use `--rehearsal` before real send when selectors or template content changed.
- Keep recipient scope tight when the request mentions only a few students.
