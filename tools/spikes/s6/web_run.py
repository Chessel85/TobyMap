"""Spike S6 in the browser: Piper's Alba voice on a web page (P0-T9, architecture 4.6 and 12.7).

Serves this repository and opens tools/spikes/s6/web in Chromium and Firefox
without a window. The page loads ONNX Runtime Web, eSpeak NG (phonemizer.js)
and the Alba voice in a worker, then speaks the eight demo labels, placed in
space with Web Audio. It times the download, loading the voice, the first
label and each label from request to sound. Each browser runs twice: first
downloading the voice, then reading it from the browser's storage, as on a
later visit. The same labels are timed here with the desktop's Piper, and the
browser's phonemes are checked against the desktop's.
Results go to docs/spikes/s6-results as plain text, and as JSON.

Run:
    .venv\\Scripts\\python.exe tools\\spikes\\s6\\web_run.py
    .venv\\Scripts\\python.exe tools\\spikes\\s6\\web_run.py --serve      (listen in your own browser)
    add --isolated to either, to let the voice use several threads

Needs: .venv\\Scripts\\python.exe tools\\fetch_vendor.py --piper, and the Alba
voice in voices\\piper (the desktop demo's voices). The desktop timing needs
requirements-spikes.txt.
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import gzip
import http.server
import json
import statistics
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "spikes" / "s3"))

import hosting  # noqa: E402  (spike S3's local server)

RESULTS = ROOT / "docs" / "spikes" / "s6-results"
VENDOR = ROOT / "web" / "vendor" / "piper"
VOICE = ROOT / "voices" / "piper" / "en_GB-alba-medium.onnx"
LABELS = ["Berlin", "Bay of Biscay", "Llívia", "Isle of Skye", "Mont Saint-Michel", "Kilimanjaro",
          "River Thames", "Saint Petersburg"]
DOWNLOAD = ["ort.wasm.min.mjs", "ort-wasm-simd-threaded.mjs", "ort-wasm-simd-threaded.wasm", "phonemizer.js"]
PAGE = "/tools/spikes/s6/web/index.html"


class IsolatedHandler(hosting.RangeHandler):
    """Sends the two headers that make a page cross-origin isolated, which a
    browser requires before a worker may use several threads."""

    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()


def start_server(isolated: bool, port: int = 0) -> hosting.LocalServer:
    server = hosting.LocalServer(ROOT, port=port)
    if isolated:  # the same server, with the isolating handler in place of the plain one
        server.server.server_close()
        handler = functools.partial(IsolatedHandler, directory=str(ROOT))
        server.server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        server.thread = threading.Thread(target=server.server.serve_forever, daemon=True)
    return server.start()


def check_files() -> None:
    missing = [n for n in DOWNLOAD if not (VENDOR / n).is_file()]
    if missing:
        raise SystemExit("ONNX Runtime Web or phonemizer.js not found in web/vendor/piper. "
                         "Run: .venv\\Scripts\\python.exe tools\\fetch_vendor.py --piper")
    if not VOICE.is_file():
        raise SystemExit(f"The Alba voice was not found: {VOICE}")


def download_lines() -> list[str]:
    """What a first visit fetches for the voice, with sizes as stored and as a server would send them compressed."""
    files = [VENDOR / n for n in DOWNLOAD] + [VOICE, VOICE.with_name(VOICE.name + ".json")]
    rows = []
    for f in files:
        data = f.read_bytes()
        rows.append((f.name, len(data), len(gzip.compress(data, compresslevel=6))))
    total, packed = sum(r[1] for r in rows), sum(r[2] for r in rows)
    lines = [f"A first visit fetches {total / 2**20:.1f} MB for the voice, or about {packed / 2**20:.1f} MB "
             "if the server compresses it (gzip):"]
    lines += [f"  {n}: {s / 2**20:.2f} MB, {z / 2**20:.2f} MB compressed" for n, s, z in rows]
    return lines


def desktop_run() -> tuple[list[str], dict]:
    import voices  # tools/spikes/s6/voices.py, with Piper from requirements-spikes.txt

    t0 = time.perf_counter()
    voice, _ = voices.load("alba")
    load_ms = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    voice.speak("Berlin")
    first_ms = (time.perf_counter() - t0) * 1000
    times, ids = [], {}
    for _ in range(2):
        for label in LABELS:
            t0 = time.perf_counter()
            voice.speak(label)
            times.append((time.perf_counter() - t0) * 1000)
    for label in LABELS:
        ids[label] = [voice.voice.phonemes_to_ids(p) for p in voice.voice.phonemize(label)]
    lines = [f"Piper with the Alba voice on the desktop, Python {sys.version.split()[0]}, "
             f"{dt.datetime.now().isoformat(timespec='seconds')}.",
             f"Loading the voice took {load_ms:.0f} ms, and the first label {first_ms:.0f} ms.",
             f"Later labels: median {statistics.median(times):.0f} ms, longest {max(times):.0f} ms, "
             "from request to sound ready to play."]
    return lines, {"load_ms": load_ms, "first_ms": first_ms, "label_ms": times, "ids": ids}


def compare_ids(browser: dict, desktop_ids: dict) -> list[str]:
    seen, differ = set(), []
    for label in browser.get("labels", []):
        if "ids" not in label or label["text"] in seen:
            continue
        seen.add(label["text"])
        if label["ids"] != desktop_ids.get(label["text"]):
            differ.append(f"  {label['text']}: browser {label['phonemes']}")
    if not seen:
        return ["No labels to compare with the desktop."]
    if not differ:
        return [f"The phonemes of all {len(seen)} labels are the same as on the desktop."]
    return [f"The phonemes of {len(differ)} of {len(seen)} labels differ from the desktop:"] + differ


def run_browser(playwright, browser: str, url: str) -> dict:
    if browser == "firefox":
        kind, options = playwright.firefox, {"firefox_user_prefs": {"media.autoplay.default": 0}}
    else:
        kind, options = playwright.chromium, {"args": ["--autoplay-policy=no-user-gesture-required"]}
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        context = kind.launch_persistent_context(profile, headless=True, **options)
        try:
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)
            first = page.evaluate("window.s6.run(true)")
            # A second run in the same browser: the voice is already stored, as on a later visit.
            second = page.evaluate("window.s6.run(false)")
            text = page.input_value("#results")
            if errors:
                text += "Errors on the page:\n" + "\n".join(errors) + "\n"
        finally:
            context.close()
    return {"text": text, "first": first, "second": second}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Spike S6: Piper's Alba voice in the browser.")
    parser.add_argument("--browsers", nargs="+", default=["chromium", "firefox"])
    parser.add_argument("--serve", action="store_true", help="serve the page for your own browser")
    parser.add_argument("--isolated", action="store_true",
                        help="serve the page cross-origin isolated, so the voice can use several threads")
    parser.add_argument("--no-desktop", action="store_true", help="skip the desktop timing")
    args = parser.parse_args(argv)
    check_files()

    if args.serve:
        server = start_server(args.isolated, port=8782)
        url = server.url + PAGE
        print(f"Spike S6 page: {url}")
        print("Press Ctrl+C in this window to stop.")
        webbrowser.open(url)
        try:
            server.thread.join()
        except KeyboardInterrupt:
            print("Stopped.")
        return 0

    from playwright.sync_api import sync_playwright

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M") + ("-isolated" if args.isolated else "")
    lines, data = ([], {"ids": {}}) if args.no_desktop else desktop_run()
    lines += download_lines()
    (RESULTS / f"{stamp}-desktop.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (RESULTS / f"{stamp}-desktop.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n".join(lines))

    server = start_server(args.isolated)
    try:
        with sync_playwright() as playwright:
            for browser in args.browsers:
                print(f"Running in {browser}.")
                out = run_browser(playwright, browser, server.url + PAGE)
                text = out["text"]
                if data["ids"]:
                    text += "\n".join(compare_ids(out["first"], data["ids"])) + "\n"
                (RESULTS / f"{stamp}-{browser}.txt").write_text(text, encoding="utf-8")
                (RESULTS / f"{stamp}-{browser}.json").write_text(
                    json.dumps({"first": out["first"], "second": out["second"]}, indent=1, ensure_ascii=False),
                    encoding="utf-8")
                print(text)
    finally:
        server.stop()
    print(f"Results saved in {RESULTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
