"""Spike S3: run the hosting and storage tests in Chromium, Firefox and Edge (P0-T6).

Starts three servers on this computer:

* the test page;
* the test file, with the permission for other web pages to read it;
* the test file, without that permission, as GitHub's download server does.

Then it opens the page in each browser, without a window, runs the reading
test on every place in the list, and the storage test, and saves the results
as text in docs/spikes/s3-results.

Run:
    .venv\\Scripts\\python.exe tools\\spikes\\s3\\run.py
    .venv\\Scripts\\python.exe tools\\spikes\\s3\\run.py --serve      (open the page in your own browser)

Options: --browsers chromium firefox msedge, --megabytes 2048, --local-only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tempfile
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import hosting  # noqa: E402

WEB = HERE / "web"
FILES = HERE / "files"
RESULTS = ROOT / "docs" / "spikes" / "s3-results"

# The TobyMap test file, if it is ever published (it needs the PO's
# permission; on 2 November the PO chose not to, so it is skipped).
TOBYMAP_RELEASE = f"https://github.com/Chessel85/TobyMap/releases/download/spike-s3/{hosting.TEST_FILE_NAME}"

# Files other projects have already published, so the hosts can be tried
# before anything of TobyMap's is published.
OTHER_PROJECTS = [
    {"name": "GitHub Releases, a file in another public project (Pyodide)",
     "url": "https://github.com/pyodide/pyodide/releases/download/0.27.0/pyodide-core-0.27.0.tar.bz2",
     "pattern": False},
    {"name": "Hugging Face, a file in another public dataset (GSM8K)",
     "url": "https://huggingface.co/datasets/openai/gsm8k/resolve/main/main/test-00000-of-00001.parquet",
     "pattern": False},
]


def published(url: str) -> bool:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def build_sources(with_cors: str, without_cors: str, local_only: bool) -> tuple[list[dict], list[str]]:
    name = hosting.TEST_FILE_NAME
    sources = [
        {"name": "This computer, with permission for other pages", "url": f"{with_cors}/{name}",
         "pattern": True, "size": hosting.TEST_FILE_SIZE},
        {"name": "This computer, without permission, as GitHub's download server",
         "url": f"{without_cors}/{name}", "pattern": True, "size": hosting.TEST_FILE_SIZE},
    ]
    notes = []
    if local_only:
        return sources, notes
    for label, url in (("TobyMap's GitHub release", TOBYMAP_RELEASE),):
        if published(url):
            sources.append({"name": f"{label}, the test file", "url": url, "pattern": True,
                            "size": hosting.TEST_FILE_SIZE})
        else:
            notes.append(f"{label}: the test file is not published there yet, so it was not tried.")
    sources.extend(OTHER_PROJECTS)
    return sources, notes


def start_servers(local_only: bool, ports=(0, 0, 0)):
    hosting.write_test_file(FILES / hosting.TEST_FILE_NAME)
    with_cors = hosting.LocalServer(FILES, allow_other_origins=True, port=ports[1]).start()
    without_cors = hosting.LocalServer(FILES, allow_other_origins=False, port=ports[2]).start()
    sources, notes = build_sources(with_cors.url, without_cors.url, local_only)
    page = hosting.LocalServer(WEB, port=ports[0],
                               extra_files={"/sources.json": json.dumps(sources).encode()}).start()
    return page, [page, with_cors, without_cors], sources, notes


def run_browser(playwright, browser: str, page_url: str, megabytes: int) -> tuple[str, dict]:
    kind = playwright.firefox if browser == "firefox" else playwright.chromium
    options = {"headless": True}
    if browser == "msedge":
        options["channel"] = "msedge"
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        context = kind.launch_persistent_context(profile, **options)
        try:
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(page_url)
            page.evaluate("window.s3.ready")
            name = page.evaluate("window.s3.browserName()")
            read = page.evaluate("window.s3.readTest(window.s3.sources())")
            storage = page.evaluate(f"window.s3.storageTest({int(megabytes)})")
            text = page.input_value("#results")
            if errors:
                text += "Errors on the page:\n" + "\n".join(errors) + "\n"
        finally:
            context.close()
    return text, {"browser": name, "read": read, "storage": storage}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Spike S3: hosting and browser storage tests.")
    parser.add_argument("--browsers", nargs="+", default=["chromium", "firefox", "msedge"])
    parser.add_argument("--megabytes", type=int, default=2048)
    parser.add_argument("--local-only", action="store_true", help="only the servers on this computer")
    parser.add_argument("--serve", action="store_true", help="serve the page for your own browser")
    args = parser.parse_args(argv)

    if args.serve:
        page, servers, sources, notes = start_servers(args.local_only, ports=(8770, 8771, 8772))
        for note in notes:
            print(note)
        url = f"{page.url}/index.html"
        print(f"Spike S3 page: {url}")
        print("Press Ctrl+C in this window to stop.")
        webbrowser.open(url)
        try:
            page.thread.join()
        except KeyboardInterrupt:
            print("Stopped.")
        return 0

    from playwright.sync_api import sync_playwright

    page, servers, sources, notes = start_servers(args.local_only)
    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    try:
        with sync_playwright() as playwright:
            for browser in args.browsers:
                print(f"Running in {browser}.")
                text, data = run_browser(playwright, browser, f"{page.url}/index.html", args.megabytes)
                if notes:
                    text += "\n".join(notes) + "\n"
                (RESULTS / f"{stamp}-{browser}.txt").write_text(text, encoding="utf-8")
                (RESULTS / f"{stamp}-{browser}.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
                print(text)
    finally:
        for server in servers:
            server.stop()
    print(f"Results saved in {RESULTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
