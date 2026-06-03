"""佛教志蓮小學 — 6至7月時間表（Streamlit）

整頁為 GitHub 同款 HTML UI；AI 查詢在第三個分頁，經 Streamlit Secrets 呼叫 DeepSeek。
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
  div[data-testid="stStatusWidget"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    overflow: hidden !important;
  }
  [data-testid="stSidebar"] { display: none !important; }
  .stApp { margin-top: 0 !important; background: #f7f5f0 !important; }
  section[data-testid="stMain"] { padding-top: 0 !important; }
  div[data-testid="stMain"] > div.block-container {
    padding: 0 !important;
    max-width: 100% !important;
  }
  div[data-testid="stHtml"] { width: 100% !important; }
  div[data-testid="stHtml"] iframe {
    border: none !important;
    width: 100% !important;
    min-height: 480px;
  }
</style>
""",
    unsafe_allow_html=True,
)

# AI 請求 + iframe 高度自動調整
components.html(
    """
<script>
(function () {
  if (window.__timetableBridge) return;
  window.__timetableBridge = true;
  function resizeFromSource(source, height) {
    const h = Math.max(480, Number(height) || 0) + 12;
    document.querySelectorAll("iframe").forEach(function (ifr) {
      if (ifr.contentWindow === source) {
        ifr.style.height = h + "px";
      }
    });
  }
  window.addEventListener("message", function (e) {
    const d = e.data;
    if (!d || !d.type) return;
    if (d.type === "timetable-resize") {
      resizeFromSource(e.source, d.height);
      return;
    }
    if (d.type !== "timetable-ai-request") return;
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
    ai_reply = {"text": answer, "requestId": ai_rid}
    for key in ("ai_q", "ai_date", "ai_rid"):
        if key in st.query_params:
            del st.query_params[key]

try:
    ui_html = load_ui_html(qp_raw, ai_reply=ai_reply)
except Exception as e:
    st.error(f"無法載入課表 UI：{e}")
    st.stop()

# st.html 比固定高度 iframe 更易保持正確比例
st.html(ui_html, width="stretch")