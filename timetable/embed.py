from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
DATA = ROOT / "data.json"
TEMPLATE = ROOT / "template.html"
BUILD = ROOT / "build.py"


def ensure_index_html() -> None:
    if not DATA.is_file():
        raise FileNotFoundError(f"Missing {DATA}")
    if not INDEX.is_file() or DATA.stat().st_mtime > INDEX.stat().st_mtime:
        if not BUILD.is_file():
            raise FileNotFoundError("index.html missing and build.py not found")
        subprocess.run(["python3", str(BUILD)], cwd=ROOT, check=True)


def strip_cloud_chat(html: str) -> str:
    """Remove in-page chat (uses /api/chat); Streamlit uses sidebar + secrets instead."""
    fab = html.find('<button id="chat-fab"')
    data_script = html.find('<script id="data"')
    if fab != -1 and data_script != -1:
        html = html[:fab] + html[data_script:]

    css_start = html.find("/* ---- AI Chatbot ---- */")
    if css_start != -1:
        mobile = html.find("  @media (max-width: 640px) {\n    .chat-panel", css_start)
        if mobile != -1:
            css_end = html.find("\n  }\n", mobile)
            if css_end != -1:
                css_end += len("\n  }\n")
                html = html[:css_start] + html[css_end:]
        else:
            css_end = html.find("body.chat-open .back-to-top", css_start)
            if css_end != -1:
                line_end = html.find("\n", css_end)
                if line_end != -1:
                    html = html[:css_start] + html[line_end + 1 :]

    js_markers = [
        "  // ---- AI Chatbot (DeepSeek V4 via Firebase /api/chat) ----",
        "  // ---- AI Chatbot",
    ]
    for marker in js_markers:
        js_start = html.find(marker)
        if js_start != -1:
            js_end = html.find("  // Initial render", js_start)
            if js_end != -1:
                html = html[:js_start] + html[js_end:]
            break

    return html


def load_ui_html() -> str:
    ensure_index_html()
    html = INDEX.read_text(encoding="utf-8")
    return strip_cloud_chat(html)