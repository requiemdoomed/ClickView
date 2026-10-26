# Verification report

Verified in the build environment on October 25, 2026 (America/Toronto).

## Executed checks

| Check | Result | Scope |
| --- | --- | --- |
| `python -m pytest -q` | 35 passed, 1 skipped | Python 3.12, Linux, Qt offscreen |
| SQLite repository | Passed | Five-item recovery, exact whitespace/Unicode, literal search, deduplication, metadata, pin-preserving clear, full clear, deletion, validation, retention, reopen persistence |
| Backup and transaction tests | Passed | JSON roundtrip, Unicode, duplicate handling, malformed records, invalid versions, rollback after a simulated database failure, retention and edit collision handling |
| Capture policy | Passed | Paused, excluded, unidentified, and permitted application inputs; common secret patterns and normal-text controls |
| Qt clipboard integration | Passed | Actual `QClipboard.setText` and `dataChanged`, five captures, search, copy restoration, no duplicate on restore, blocked captures including a private-key header |
| Browser integration | Passed | Chromium 134 headless, real browser clipboard API, search, pin, category, reload, add/delete/clear, HTML treated as text, empty search, backup export decoded by Python, valid/invalid imports, text edits, theme persistence, pin-preserving clear, storage-quota rollback and corrupted-history preservation, no page-script errors |
| Responsive layout | Passed | 1440px desktop and 390px mobile; no horizontal document overflow |
| Python compilation / JS syntax | Passed | `compileall` and `node --check web.js` |
| Live MySQL integration | Skipped | No MySQL server in this build environment |
| Windows/macOS native sessions | Not executed | CI workflow included; real foreground apps and permission prompts require manual checks |

The Qt test injects a deterministic foreground-app name and uses Qt's offscreen clipboard. It is **not** an end-to-end test of copying from an external Windows/macOS/Linux application. Browser screenshots are actual rendered application captures using the labeled examples. No model training is needed or performed.

The 1.1 upgrade also passed static Python checks (`ruff check --select F`) and formatting checks. Fault-injection tests deliberately raise storage/database errors; they validate recovery behavior and do not claim those errors happened to user data.

A first browser run found that the mobile stylesheet hid Clear history. The mobile layout was corrected to retain clear-history and category controls, and the browser check passed after the fix.

## Repeat locally

From the repository root:

```bash
python -m pip install -e ".[test]"
python -m pytest -q
python -m compileall -q clipview
node --check web.js
```

Optional browser checks (starts its own local server):

```bash
python -m pip install playwright
python -m playwright install chromium
python tests/browser_check.py
```

The browser script writes fresh demo screenshots under `docs/`. For a specific installed browser binary, set `CHROMIUM_PATH`. The verification here used Playwright 1.51.0 and Chromium 134 because the newer browser download was unavailable.

For MySQL, the workflow starts a disposable MySQL 8.4 service, sets `CLIPVIEW_TEST_MYSQL=1` and `CLIPVIEW_TEST_PASSWORD`, and runs `tests/test_mysql.py`. The test clears the entire `clipview_test` database table. Never point this test at personal history. CI jobs are supplied, not claimed as already run.

## Native acceptance checklist

1. Start ClipView on the target desktop; verify it begins paused and contains no sample history.
2. Click Start capture, switch to a text editor, and copy five different snippets.
3. Return to ClipView, search for the third, restore it, and paste into the editor. Verify exact whitespace.
4. Pin and categorize a snippet; restart the app and verify persistence.
5. Add the editor's process-name fragment to App exclusions; copy new text in it and verify that text is absent. Repeat with a password manager and with detection permission denied.
6. Pause capture, copy text, resume, and verify the paused text was not saved retroactively.
7. Delete one item, clear ordinary history while keeping pins, then clear everything including pins.
8. Repeat with the local MySQL backend, including stopping the server to check the error message.
9. Export a backup, import it into an empty installation, and verify dates, categories, and pins. Test a malformed file and confirm no partial import.
10. Test light/dark themes and editing; try editing text into an existing duplicate.
11. Apply short retention to an old unpinned test snippet and verify a pinned one is kept.
12. On macOS, check System Events permissions and capture timing when returning to the app. On Linux Wayland, confirm capture is blocked and manual Add text works.

Passing automated checks does not guarantee a bug-free application on every platform. Foreground attribution remains best effort; exclusions cannot identify individual browser tabs or guarantee that secrets will never be saved.
