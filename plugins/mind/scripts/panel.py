#!/usr/bin/env python3
"""The mind panel's entry point: reads the user's own logs, transcripts and memory files and writes one page."""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mind import __version__, collect  # noqa: E402


def say(text: str) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    print(text)


def build(cfg: dict, transcripts: bool) -> dict:
    return collect.collect(cfg, transcripts=transcripts)


def serve(cfg: dict, port: int, lang: str, transcripts: bool) -> int:
    """A page for this machine only (127.0.0.1); the data is collected at most once a minute."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from mind import render
    lock, held = threading.Lock(), {"at": 0.0, "data": None}

    def data() -> dict:
        with lock:
            if held["data"] is None or time.time() - held["at"] >= 60:
                held["data"], held["at"] = build(cfg, transcripts), time.time()
            return held["data"]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (the name http.server calls)
            path = self.path.split("?")[0]
            if path == "/":
                body, kind = render.page(data(), lang, served=True).encode("utf-8"), "text/html; charset=utf-8"
            elif path == "/data.json":
                body, kind = json.dumps(data(), ensure_ascii=False).encode("utf-8"), "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    say(f"mind panel: http://127.0.0.1:{port}/ (Ctrl+C stops it)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(prog="panel", description="Living Runtime mind panel: one local page from your own "
                                                           "files")
    ap.add_argument("--version", action="version", version=f"mind {__version__}")
    ap.add_argument("--out", help="where the page goes (default <mind folder>/panel.html)")
    ap.add_argument("--open", action="store_true", help="open the page in the browser")
    ap.add_argument("--serve", type=int, metavar="PORT", help="serve the page on 127.0.0.1:PORT")
    ap.add_argument("--lang", choices=("en", "tr"))
    ap.add_argument("--config", help="a config JSON (default <mind folder>/config.json)")
    ap.add_argument("--scorecard", help="a scorecard JSON")
    ap.add_argument("--no-transcripts", action="store_true", help="skip the transcript scan")
    ap.add_argument("--json", action="store_true", help="print the collected data instead of writing the page")
    a = ap.parse_args(argv)
    cfg = collect.load_config(a.config)
    if a.scorecard:
        cfg["scorecard"] = a.scorecard
    lang = a.lang or cfg.get("lang") or "en"
    cfg["lang"] = lang
    transcripts = not a.no_transcripts
    if a.serve:
        return serve(cfg, a.serve, lang, transcripts)
    data = build(cfg, transcripts)
    if a.json:
        say(json.dumps(data, ensure_ascii=False, indent=1))
        return 0
    from mind import render
    out = Path(a.out) if a.out else Path(cfg["mind"]) / "panel.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(render.page(data, lang))
    say(str(out))
    if a.open:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
