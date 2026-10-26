---
name: admin-gbetalk
description: Archive received GBTalk notes to local Markdown with resumable checkpoints. Use when collecting notes from the GBTalk Message Manager; never send or reply to notes.
---

# GBTalk note archive

Use this skill to collect received notes from the GBTalk **쪽지관리함** into local monthly Markdown. The archive is local; this workflow does not send, forward, or reply to messages.

## Collection workflow

1. Read `NEXT_STEPS.md` for the current archive boundary and known UI behavior. Use the running GBTalk main window and open **쪽지 → 쪽지관리함**. Do not choose among same-titled individual `받은 쪽지읽기` windows.
2. Use the Computer Use skill for all Windows app interactions. Select the unique `쪽지관리함` window from the current app inventory, inspect its state, and refresh accessibility state after each navigation action.
3. For a fresh full-list pass, focus the inbox list and use `Home` to select the newest row; confirm its visible header and body before capture. `Home` selected the first visible note in the current test. Then one `↓` advanced from 2026-10-23 09:45 to 08:49. Refresh the state after every move and wait until the row and body agree; a first response was stale once. Do not assume a selection survived search, tab closure, or other view changes.
4. Read received date/time and sender from the selected row/header. Do not infer received time from a forwarded message header inside the body; those timestamps can differ. The UIA list control exposes the selected row and body but not reliable received date/sender fields, so use the visible row/header for those fields and stop if either is unreadable. Read the full body from its UIA value when available. Otherwise click the body edit control identified in the latest tree, verify that it has focus, then use `Ctrl+A`, `Ctrl+C` and compare the clipboard to the UIA body. A live copy matched after normalizing line-break formatting. A tested return path from body focus is `Shift+Tab` twice back to the selected list row; verify the focus before sending `↓` again.
5. Keep the loop non-destructive: never send `Delete`, `Enter`, or `Space` to an uncertain focus. `Tab` from the body reached its scrollbar and then the **삭제** button in a test; do not send a fixed Tab sequence. The raw capture helper sends only focus-return `Shift+Tab`, list `Home`, and row `Down` keys. A repeated adjacent row/body pair is ambiguous, so stop and inspect rather than silently skipping or duplicating it. Non-adjacent identical bodies are retained as separate notes.
6. For fast raw staging, use `scripts/capture_macro.mjs` with the Computer Use `sky` client. It reads each selected body from the UIA value, fingerprints the selected row and body, and writes synced JSONL/checkpoint data in batches of at most 30. It does not save screenshots or message attachments. This raw JSONL has no verified `received_at` or sender/title metadata, so do not pass it to `archive-batch` until that metadata has been reconciled. For final monthly storage, produce a separate JSONL with `received_at`, `title`, and `body`, then run `gbtalk_summary.py archive-batch <file> --before YYYY-MM-DD --period month`.
7. Inspect each 30-note batch before starting the next: confirm sequential JSONL rows, body hashes, checkpoint prefix hash, and no adjacent row-fingerprint repeats. On restart, validate the saved prefix and resume cursor; if the cursor cannot be matched, the helper scans from `Home` and checks all saved rows before continuing. A two-minute unattended run remains a speed target, not a promise. Computer Use input brings the manager to the foreground, so background use is not guaranteed.

See `README.md` for commands and archive behavior, and `NEXT_STEPS.md` for current verification results and the next implementation steps.

When designing or changing a keyboard-driven UI loop, read [references/keyboard-macro-methodology.md](references/keyboard-macro-methodology.md) for the reusable probing, focus, batching, and recovery method.
