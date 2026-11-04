---
name: ego-browser
description: Use Ego Lite's ego-browser CLI to inspect and operate browser pages, especially signed-in web apps and multi-step forms. Use when the user asks to use Ego Lite or its existing pages.
---

# Ego Browser

Use Ego Lite's supported browser API for browser work. Read the installed CLI guide at the start of a browser task with `ego-browser skill`; the installed guide is authoritative for the current version.

## Workflow

- Use one TaskSpace for one user goal. Inspect `listTaskSpaces()`, `task.tabs()`, and `task.userPage()` before acting so you know whether the user's visible page is available.
- A TaskSpace-managed page can be separate from the user's currently visible browser tab. Do not imply that the user's visible tab changed unless its URL or page state confirms that. When a supplied URL is the intended target and no user page is available, work in the managed page, then keep the result page and tell the user where the work happened.
- Reuse the same TaskSpace and Page across rounds. Do not open another TaskSpace to recover from an error or unexpected state.
- Prefer snapshots and accessible selectors for ordinary web pages. Use screenshots for visual confirmation, canvas editors, or when the user asks to see the resulting screen.
- Before editing a form, inspect current values and preserve correct existing entries. Use the user's supplied content, check the resulting page state, and save when the application provides a save action.
- Verify the saved status and key field values before finishing. Keep the result page only when the user needs to view or continue it; otherwise finish with no kept pages.
- Keep task scripts, logs, screenshots, and exports under a named subfolder in `artifacts/` or `records/`. Do not leave task output in this skill folder's root.
- Do not download or submit externally unless the user requested it or the request clearly includes that action.

## References

- Read [references/troubleshooting.md](references/troubleshooting.md) when the expected user tab is missing, the browser appears unchanged, or a page action fails.
- Use the task-specific record in `records/` and its artifact directory as examples of how to document a completed workflow.
