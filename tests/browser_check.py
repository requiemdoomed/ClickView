"""Run from the repository root with Playwright installed; starts a temporary local server."""

from playwright.sync_api import sync_playwright
import os
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

server = ThreadingHTTPServer(("127.0.0.1", 0), SimpleHTTPRequestHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()

with sync_playwright() as p:
    args = {"headless": True, "args": ["--no-sandbox"]}
    if os.getenv("CHROMIUM_PATH"):
        args["executable_path"] = os.environ["CHROMIUM_PATH"]
    browser = p.chromium.launch(**args)
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 960},
        permissions=["clipboard-read", "clipboard-write"],
    )
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{server.server_port}")
    assert page.locator(".card").count() == 0
    page.locator("#load").click()
    assert page.locator(".card").count() == 5
    page.locator("#search").fill("SELECT")
    assert page.locator(".card").count() == 1
    page.locator("#copy").click()
    assert page.evaluate("navigator.clipboard.readText()").startswith("SELECT title")
    page.locator("#category").fill("Code")
    page.locator("#save").click()
    page.locator("#pin").click()
    page.reload()
    page.locator("#pins").click()
    assert page.locator(".card").count() == 1
    assert page.locator("#category").input_value() == "Code"
    page.locator("#all").click()
    page.locator("#theme").click()
    assert page.locator("body").evaluate("e=>e.classList.contains('light')")
    page.reload()
    assert page.locator("body").evaluate("e=>e.classList.contains('light')")
    page.screenshot(path="docs/light-demo.png", full_page=True)
    page.locator("#theme").click()
    page.locator("#edit").click()
    page.locator("#text").fill("SELECT edited FROM notes;")
    page.locator("#form .primary").click()
    assert page.locator("#body").inner_text() == "SELECT edited FROM notes;"
    with page.expect_download() as download:
        page.locator("#export").click()
    from clipview.backup import decode_backup
    from pathlib import Path

    raw = Path(download.value.path()).read_text()
    assert len(decode_backup(raw)) == 5
    page.on("dialog", lambda d: d.accept())
    page.locator("#clear").click()
    page.locator("#confirm-clear").click()
    assert page.locator(".card").count() == 1
    page.locator("#import-file").set_input_files(
        {"name": "backup.json", "mimeType": "application/json", "buffer": raw.encode()}
    )
    page.wait_for_function("document.querySelectorAll('.card').length===5")
    assert page.locator(".card").count() == 5
    page.locator("#import-file").set_input_files(
        {
            "name": "bad.json",
            "mimeType": "application/json",
            "buffer": b'{"format":"clipview","version":1,"clips":[{"body":"bad"}]}',
        }
    )
    page.wait_for_function(
        "document.querySelector('#toast').textContent.startsWith('Import failed:')"
    )
    assert page.locator(".card").count() == 5
    page.locator("#all").click()
    page.locator("#toast").wait_for(state="hidden")
    page.screenshot(path="docs/browser-demo.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(path="docs/mobile-demo.png", full_page=True)
    page.locator("#add").click()
    page.locator("#text").fill("<img src=x onerror=alert(1)>")
    page.locator("#form .primary").click()
    assert page.locator("#body").inner_text() == "<img src=x onerror=alert(1)>"
    assert page.locator("#body img").count() == 0
    page.locator("#delete").click()
    assert page.locator(".card").count() == 5
    page.locator("#clear").click()
    page.locator("#include-pins").check()
    page.locator("#confirm-clear").click()
    assert page.locator(".card").count() == 0
    page.reload()
    assert page.locator(".card").count() == 0
    page.locator("#search").fill("nothing")
    assert "No matches" in page.locator("#list").inner_text()
    page.locator("#search").fill("")
    page.evaluate(
        "() => { Storage.prototype.setItem = function(){throw new DOMException('Full','QuotaExceededError')}; }"
    )
    page.locator("#load").click()
    assert page.locator(".card").count() == 0
    assert page.locator("#storage-warning").is_visible()
    page.reload()
    assert page.locator(".card").count() == 0
    # Corrupt storage must not be overwritten by an ordinary add.
    page.evaluate("localStorage.setItem('clipview.history.v1','broken-json')")
    page.reload()
    page.locator("#load").click()
    assert page.evaluate("localStorage.getItem('clipview.history.v1')") == "broken-json"
    page.locator("#clear").click()
    page.locator("#include-pins").check()
    page.locator("#confirm-clear").click()
    assert page.evaluate("localStorage.getItem('clipview.history.v1')") == "[]"
    assert not errors, errors
    browser.close()
    print(
        "Browser checks passed: backup interchange, malformed import rejection, quota rollback, corrupt-storage preservation, light-mode persistence, editing, pin-preserving clear;  five-copy recovery, real clipboard restore, categories, pins, reload, deletion, clear, mobile layout, literal HTML, no script errors."
    )
