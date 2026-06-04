"""佛教志蓮小學 — 6至7月時間表（Streamlit）

整頁為 GitHub 同款 HTML（必須用 components.html 嵌入，st.html 唔會跑 JS）。
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from timetable.chat import ask_timetable
from timetable.embed import load_ui_html, pick_boot_params

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
  .stAppHeader {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
  }
  [data-testid="stSidebar"] { display: none !important; }
  .stApp { background: #f7f5f0 !important; }
  html, body, .stApp, [data-testid="stAppViewContainer"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
  }
  section[data-testid="stMain"],
  div[data-testid="stMain"],
  [data-testid="stVerticalBlock"],
  .block-container,
  section.main {
    padding-top: 0 !important;
    margin-top: 0 !important;
  }
  div[data-testid="stMain"] > div.block-container {
    padding: 0 !important;
    max-width: 100% !important;
  }
  iframe { border: none !important; width: 100% !important; margin: 0 !important; }
</style>
""",
    unsafe_allow_html=True,
)

components.html(
    """
<script>
(function () {
  if (window.__timetableBridge) return;
  window.__timetableBridge = true;
  window.addEventListener("message", function (e) {
    const d = e.data;
    if (!d || d.type !== "timetable-ai-request") return;
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("ai_q", d.question || "");
      url.searchParams.set("ai_date", d.anchorDate || "");
      url.searchParams.set("ai_rid", d.requestId || String(Date.now()));
      window.location.replace(url.toString());
    } catch (_) {}
  });
})();
</script>
""",
    height=0,
)

qp_raw = dict(st.query_params)
processed: set[str] = st.session_state.setdefault("ai_processed", set())


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

if ai_q and ai_rid and ai_rid not in processed:
    processed.add(ai_rid)
    anchor = ai_date or pick_boot_params(qp_raw).get("dayDate", "")
    try:
        answer = ask_timetable(ai_q, anchor)
    except Exception as e:
        answer = f"❌ {e}"
    ai_reply = {"text": answer, "requestId": ai_rid, "question": ai_q}
    for key in ("ai_q", "ai_date", "ai_rid"):
        if key in st.query_params:
            del st.query_params[key]

try:
    ui_html = load_ui_html(qp_raw, ai_reply=ai_reply)
except Exception as e:
    st.error(f"無法載入課表 UI：{e}")
    st.stop()

# 必須用 components.html：iframe 內可執行課表 JS（st.html 官方唔支援 JS）
components.html(ui_html, height=1500, scrolling=True)