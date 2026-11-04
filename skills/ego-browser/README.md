# Ego Browser

Reusable guidance and work records for browser automation through Ego Lite's `ego-browser` CLI.

## What's here

- `SKILL.md` — when to use Ego Browser and the shared workflow.
- `references/troubleshooting.md` — TaskSpace visibility, target selection, and save verification notes.
- `records/` — dated summaries of completed browser tasks and any user-visible caveats.
- `artifacts/` — per-task screenshots, text exports, and other deliverables.

## Operating notes

Ego Browser may control a TaskSpace-managed page that is distinct from the browser tab the user is watching. Check the Page URL and title, keep the result page when useful, and give the user a screenshot or a direct description of the final state. Do not claim that the user's visible tab changed without checking it.

Store each task under a dated, descriptive subfolder, for example:

```text
artifacts/2026-11-03-aiedap-lesson-12134/
```

Keep reusable workflow instructions in `SKILL.md` or `references/`; keep task-specific logs and exports under `records/` and `artifacts/`.
