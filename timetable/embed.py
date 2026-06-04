from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
DATA = ROOT / "data.json"
BUILD = ROOT / "build.py"

BOOT_KEYS = (
    "tab",
    "dayDate",
    "teacherDate",
    "teacherName",
    "matrixMode",
    "matrixClass",
    "matrixPeriod",
    "aiMode",
    "aiReply",
    "aiReplyId",
)


def ensure_index_html() -> None:
    if not DATA.is_file():
        raise FileNotFoundError(f"Missing {DATA}")
    if not INDEX.is_file() or DATA.stat().st_mtime > INDEX.stat().st_mtime:
        if not BUILD.is_file():
            raise FileNotFoundError("index.html missing and build.py not found")
        subprocess.run(["python3", str(BUILD)], cwd=ROOT, check=True)


def pick_boot_params(query: dict | None) -> dict[str, str]:
    if not query:
        return {}
    out: dict[str, str] = {}
    for key in BOOT_KEYS:
        val = query.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            val = val[0] if val else ""
        out[key] = str(val).strip()
    return out


def inject_streamlit_boot(html: str, boot: dict[str, str]) -> str:
    if not boot:
        return html
    payload = json.dumps(boot, ensure_ascii=False)
    snippet = (
        f'<script id="streamlit-boot">window.__STREAMLIT_BOOT__ = {payload};</script>\n'
    )
    marker = '<script id="data" type="application/json">'
    if marker not in html:
        raise ValueError("Cannot inject Streamlit boot params into timetable HTML")
    return html.replace(marker, snippet + marker, 1)


def load_ui_html(
    query: dict | None = None,
    *,
    ai_reply: dict[str, str] | None = None,
    chat_history: list[dict[str, str]] | None = None,
) -> str:
    ensure_index_html()
    html = INDEX.read_text(encoding="utf-8")
    boot = pick_boot_params(query)
    boot["aiMode"] = "streamlit"
    if chat_history:
        boot["chatHistory"] = chat_history[-12:]
    if ai_reply:
        boot["aiReply"] = ai_reply.get("text", "")
        boot["aiReplyId"] = ai_reply.get("requestId", "")
        boot["aiQuestion"] = ai_reply.get("question", "")
    return inject_streamlit_boot(html, boot)
