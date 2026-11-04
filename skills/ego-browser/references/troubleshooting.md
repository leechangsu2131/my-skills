# Ego Browser: troubleshooting

## User says the browser did not change

Ego Lite can expose a managed TaskSpace Page that is not the tab currently visible to the user. Before editing, inspect `task.tabs()` and `task.userPage()` and confirm the target URL and title. If the visible user page is unavailable, use the supplied URL in the managed Page only when that URL is the intended target; keep the result Page when the user needs to inspect it and state clearly that it was a managed Page.

Do not say that the user's visible window changed based only on an action receipt. Confirm the URL or page state. A screenshot is useful when the user asks to see the final screen.

## Page appears empty or still loading

Use a snapshot to identify the current state. Wait for an observable page condition, such as the loading message disappearing or the expected form appearing, instead of assuming the first snapshot is final. If login state or saved data is still loading, inspect again before editing.

## A control does not accept a click

After a failed action, inspect the current page before retrying. For custom select controls, the text input may be covered by its visible wrapper; target the accessible control or visible wrapper identified by a fresh snapshot. Do not reuse stale refs after the page changes.

## Changes appear but may not be saved

Check the app's saved indicator and key values after editing. Use the explicit save control if the form provides one, then confirm the resulting status. If an option such as `없음` is absent from a tool dropdown and the user said blank is acceptable, leave that field blank and record the choice.

## Download/update notices

Save browser downloads to the task's artifact subfolder before the Ego round ends. If Ego Lite reports an update notice, finish the current browser task and tell the user; do not run `ego-browser upgrade` without approval.
