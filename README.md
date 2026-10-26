# [ClipView](https://requiemdoomed.github.io/ClickView/)

**Find that line you copied.** A searchable clipboard history by **Swayam Shakya**.

ClipView keeps useful text close: code fragments, class notes, messages, and the little things you would otherwise have to recreate. The Python desktop app saves clipboard changes while running. The responsive browser demo lets you try the same workflow with explicitly pasted text.

![ClipView browser demo](docs/browser-demo.png)

<details>
<summary>Native desktop app and mobile demo</summary>

![Native desktop app](docs/desktop.png)

<img src="docs/mobile-demo.png" width="320" alt="ClipView mobile browser demo">

</details>

## What you can do

- Capture text, search its full contents, and copy it back without changing whitespace.
- Pin favorites and assign your own categories.
- Keep history across restarts; repeated copies update the existing item.
- Pause capture, exclude applications, delete individual snippets, or clear history.
- Edit saved text without losing its pin, category, or original copy date.
- Export and import versioned JSON backups between the desktop and browser versions.
- Choose light or dark mode, sort oldest/newest first, and keep pins when clearing history.
- Configure automatic age cleanup and skip several common secret formats on desktop.
- Use SQLite immediately or connect to a local MySQL database.
- Try the responsive HTML/CSS/JavaScript demo on desktop or mobile.

## Run the desktop app

Python 3.10+ is required. Python 3.12 is the CI target. From this repository folder:

```bash
python -m venv .venv
```

Activate it on **Windows PowerShell**:

```powershell
.venv\Scripts\Activate.ps1
```

Or on **macOS / Linux**:

```bash
source .venv/bin/activate
```

Then:

```bash
python -m pip install -e ".[test]"
python -m clipview
```

Click **Start capture**, switch to another app, and copy some text. Search, select a result, and click **Copy** to restore it. **Ctrl+F** (Command+F on macOS) focuses search; **Ctrl+N** opens Add text. Closing the window quits capture; there is no hidden background service or automatic startup.

**Linux X11:** install `xdotool` using your distribution's package manager for app detection. **Wayland:** automatic capture is deliberately blocked because this implementation cannot identify the foreground app reliably; use **Add text**. **macOS:** foreground detection uses System Events and may need Automation permission. Qt may report external clipboard changes only when ClipView becomes active; return to the app after copying. Windows foreground detection uses the process name. Native Windows/macOS behavior still needs the manual checks in [TESTING.md](docs/TESTING.md).

## GitHub Pages demo

Upload the entire repository. In GitHub, open **Settings → Pages**, choose **Deploy from a branch**, choose your branch and **/(root)**, and save. The entry point is `index.html`, which loads `web.css` and `web.js`. No Python server, API key, database credentials, or build step is needed for Pages.

To preview locally:

```bash
python -m http.server 8000
```

Open `http://localhost:8000`. The server above only serves the static demo. It does not run or connect to the desktop app. Browser clipboard copying needs HTTPS or localhost and user permission. If access is denied, select and copy the preview manually.

### The five-copy demo

1. Click **Try five examples** to add five clearly labeled example snippets.
2. Search for `SELECT`.
3. Select the SQL query (the third example).
4. Click **Copy snippet** and paste it into an editor.
5. Pin it, assign `Code` as its category, and reload to check persistence.

Alternatively, use **Add snippet** five times with your own text. The desktop equivalent is to copy five items from another app while capture is enabled. Examples are not inserted into the desktop database, and no training data or trained model is involved.

## New in 1.1

**Desktop:** open **Tools & settings** for backup import/export, retention, themes, and the secret-pattern guard. **Edit text** changes a saved snippet while retaining its metadata; editing into an existing snippet is rejected to prevent accidental merging. App exclusions and secret patterns apply to automatic capture, not deliberate manual entry or backup imports.

**Browser:** use **Theme**, **Import**, and **Export** in the sidebar (also available on mobile). Backups transfer text, categories, pins, and copy dates. Import merges new text and keeps existing duplicates unchanged. The clear-history dialog preserves pins unless you opt to remove them. Ctrl/Command+K focuses search.

**Backup limits:** at most 2,000 records and 10 MB per file. Invalid files are rejected before changes are saved; desktop imports use one transaction. Imports that would exceed the history count limit are rejected rather than silently discarding old text. Backups are unencrypted JSON, so store them privately. Desktop collections with more than 2,000 records including pins cannot be exported in one backup.

**Age retention:** 0 days (the default) disables age cleanup. A positive value removes older unpinned items when applied, on launch, after import, and once per hour while running. Pinned items are exempt. This is permanent deletion, so export anything you need first.

**Safer failures:** database transactions roll back incomplete changes. A database or file-access error pauses desktop capture and displays an error. Browser quota or storage-denial failures roll back the attempted change and display a persistent warning. Unreadable saved history is preserved until you explicitly clear it. Open tabs refresh when another tab changes history; simultaneous writes are not a substitute for a synchronized database.

See [CHANGELOG.md](CHANGELOG.md) for fixes and [the limitations review](docs/LIMITATIONS.md) for remaining constraints.

## Use MySQL

SQLite is the default so the app works without installing a server. For MySQL, install and start a local MySQL 8 server, then run [docs/mysql.sql](docs/mysql.sql) after replacing its password placeholder. The app creates the `clips` table on startup.

Set environment variables in the same terminal before launching. On macOS/Linux:

```bash
export CLIPVIEW_DB=mysql
export CLIPVIEW_MYSQL_HOST=127.0.0.1
export CLIPVIEW_MYSQL_PORT=3306
export CLIPVIEW_MYSQL_DATABASE=clipview
export CLIPVIEW_MYSQL_USER=clipview
export CLIPVIEW_MYSQL_PASSWORD='your-own-password'
python -m clipview
```

In PowerShell use `$env:CLIPVIEW_DB = "mysql"` and the same `$env:NAME = "value"` pattern for each setting. A `.env` file is not loaded automatically. Do not commit passwords. SQLite and MySQL are separate histories; switching does not migrate existing snippets. This configuration is intended for a local server, not an exposed remote database.

## Privacy and limits

- Capture starts paused on every launch and ignores the clipboard contents already present at startup.
- Exclusions match app-name fragments, ignoring case. Bitwarden, 1Password, KeePass, and LastPass are excluded initially. You can add more in **App exclusions**.
- Unknown foreground applications are skipped. The foreground app is a best-effort signal, not proof of which process wrote the clipboard. Background changes, browser password managers, and rapid focus changes can evade app exclusions. Pause before copying secrets. Individual browser tabs and password fields cannot be recognized.
- The default secret guard skips common private-key headers, GitHub token formats, AWS access-key IDs, and long `sk-` token patterns. It does not detect all passwords or secrets and may reject text describing those formats. Disable it only intentionally in Tools & settings.
- Saved history is **plain text**, not a password vault. Local disk encryption and OS-account protection are recommended. No clipboard contents are written to diagnostic logs.
- A snippet can contain up to 100,000 UTF-8 bytes. The desktop retains the latest 2,000 unpinned snippets; pins remain until explicitly deleted. Search scans saved text, so very large pinned collections can be slower.
- SQLite lives under Qt's application-local data directory (`ClipView/history.sqlite3`). The desktop clear dialog preserves pins unless selected otherwise and also clears the current system clipboard. Logical deletion is not a promise of secure erasure from disk, database logs, or backups.
- The web demo uses this browser's localStorage, with a 2,000-snippet cap and the browser's storage quota. It is separate from desktop history. Clearing it does not erase the system clipboard. Failed history writes are rolled back and shown in a persistent warning; theme changes may last only for the current session if preferences cannot be saved.
- The mobile experience is a responsive browser demo, not a native Android/iOS clipboard monitor. Browsers cannot silently monitor your other apps.

## Structure

```text
clipview/       PySide6 interface, capture policy, database repository
index.html      GitHub Pages demo entry
web.css         Responsive demo styles
web.js          Browser-only history and interactions
tests/          Repository, privacy, Qt clipboard, optional MySQL tests
docs/           Screenshots, verification notes, MySQL setup
.github/        Windows/macOS/Linux and MySQL test workflow
```

Qt's `dataChanged` event passes through the capture policy, then the repository saves the text. The desktop queries that repository for search and editing. The browser demo is independent and uses safe text rendering, not HTML interpolation of snippet content.

## Tests and verification

```bash
python -m pytest -q
```

Read [the verification report](docs/TESTING.md) for exactly what was run and what remains platform-dependent. Tests use temporary databases and explicit deterministic inputs; they are regression tests, not training data. GitHub Actions includes an isolated MySQL service, a desktop OS matrix, and browser checks. Those jobs must run on your repository before their results can be claimed.

Implementation references: [Qt clipboard](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QClipboard.html), [Python sqlite3](https://docs.python.org/3/library/sqlite3.html), and [PyMySQL](https://pymysql.readthedocs.io/en/latest/).

## License

[MIT](LICENSE) · Copyright © 2026 Swayam Shakya. Third-party dependencies retain their own licenses.
