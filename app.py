"""佛教志蓮小學 — 6至7月時間表（Streamlit）

整頁為 GitHub 同款 HTML（必須用 components.html 嵌入，st.html 唔會跑 JS）。
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from timetable.chat import ask_timetable
from timetable.embed import load_ui_html, pick_boot_params

ROOT = Path(__file__).resolve().parent
TIMETABLE_COMPONENT = components.declare_component(
    "timetable_ui",
    path=ROOT / "streamlit_component",
)

st.set_page_config(
    page_title="佛教志蓮小學 — 時間表查詢",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
  #MainMenu, footer { visibility: hidden; height: 0; }
  header[data-testid="stHeader"],
  [data-testid="stToolbar"],
  [data-testid="stDecoration"],
  div[data-testid="stStatusWidget"],
  [data-testid="stHeader"],
  .stAppHeader,
  .stHeader {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  [data-testid="stSidebar"] { display: none !important; }
  .stApp { background: #f7f5f0 !important; }
  html, body, .stApp, [data-testid="stAppViewContainer"], .stAppViewContainer {
    padding-top: 0 !important;
    margin-top: 0 !important;
  }
  section[data-testid="stMain"],
  div[data-testid="stMain"],
  [data-testid="stVerticalBlock"],
  .block-container,
  section.main,
  .stMainBlockContainer,
  [data-baseweb="block"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
  }
  div[data-testid="stMain"] > div.block-container {
    padding: 0 !important;
    max-width: 100% !important;
  }
  iframe { border: none !important; width: 100% !important; margin: 0 !important; padding: 0 !important; }
  /* Extra aggressive for Cloud viewer */
  .stApp > div:first-child,
  .stApp > div:first-child > div:first-child {
    padding-top: 0 !important;
    margin-top: 0 !important;
  }
</style>
""",
    unsafe_allow_html=True,
)

qp_raw = dict(st.query_params)
processed: set[str] = st.session_state.setdefault("ai_processed", set())
chat_history: list[dict[str, str]] = st.session_state.setdefault("chat_history", [])


def _qp_one(key: str) -> str:
    val = qp_raw.get(key)
    if val is None:
        return ""
    if isinstance(val, list):
        return str(val[0] if val else "").strip()
    return str(val).strip()


ai_q = _qp_one("ai_q")
ai_date = _qp_one("ai_date")
ai_rid = _qp_one("ai_rid")
ai_reply: dict[str, str] | None = None


def _clean_component_history(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, str]] = []
    for item in value[-8:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            out.append({"role": role, "content": content[:1200]})
    return out


def process_ai_request(
    question: str,
    anchor_date: str,
    request_id: str,
    history: list[dict[str, str]] | None = None,
) -> bool:
    question = (question or "").strip()
    request_id = (request_id or "").strip()
    if not question or not request_id or request_id in processed:
        return False

    processed.add(request_id)
    anchor = anchor_date or pick_boot_params(qp_raw).get("dayDate", "")
    recent_history = history or chat_history
    try:
        answer = ask_timetable(question, anchor, history=recent_history)
    except Exception as e:
        answer = f"❌ {e}"
    updated_history = (recent_history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ])[-12:]
    st.session_state["chat_history"] = updated_history
    st.session_state[f"ai_reply_{request_id}"] = {
        "text": answer,
        "requestId": request_id,
        "question": question,
        "history": updated_history,
    }
    return True


# Process incoming AI request from query params for backwards compatibility.
if process_ai_request(ai_q, ai_date, ai_rid):
    # Clear the trigger params cleanly
    for key in ("ai_q", "ai_date", "ai_rid"):
        st.query_params.pop(key, None)
    # Rerun with clean URL so the next execution can safely inject the stored reply
    st.rerun()

# Pick up any stored AI reply from a previous processing (one-shot)
for k in list(st.session_state.keys()):
    if k.startswith("ai_reply_"):
        ai_reply = st.session_state.pop(k)
        break

try:
    ui_html = load_ui_html(
        qp_raw,
        ai_reply=ai_reply,
        chat_history=st.session_state.get("chat_history", []),
    )
except Exception as e:
    st.error(f"無法載入課表 UI：{e}")
    st.stop()

component_event = TIMETABLE_COMPONENT(html=ui_html, height=5200, key="timetable_ui")
if isinstance(component_event, dict) and component_event.get("type") == "timetable-ai-request":
    did_process = process_ai_request(
        str(component_event.get("question") or ""),
        str(component_event.get("anchorDate") or ""),
        str(component_event.get("requestId") or ""),
        _clean_component_history(component_event.get("history")),
    )
    if did_process:
        st.rerun()
