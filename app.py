"""佛教志蓮小學 — 6至7月時間表（Streamlit）

主畫面：GitHub 同款 index.html（完整 UI）
側欄：AI 問答（DeepSeek / Streamlit Secrets）
網址參數：?tab=day&dayDate=2026-06-10&teacherName=李&matrixMode=table…
"""
from __future__ import annotations

from datetime import date

import streamlit as st
import streamlit.components.v1 as components

from timetable.chat import ask_timetable
from timetable.data import day_options, load_data
from timetable.embed import load_ui_html, pick_boot_params

st.set_page_config(
    page_title="佛教志蓮小學 — 時間表查詢",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
  header[data-testid="stHeader"] { background: transparent; }
  div[data-testid="stMain"] > div.block-container {
    padding-top: 0.25rem;
    padding-bottom: 0;
    max-width: 100%;
  }
  iframe { border: none !important; width: 100% !important; }
  [data-testid="stSidebar"] { min-width: 300px; }
</style>
""",
    unsafe_allow_html=True,
)

data = load_data()
day_opts = day_options(data)
default_date = date.today().isoformat()
if not any(d[0] == default_date for d in day_opts):
    default_date = day_opts[0][0] if day_opts else ""

boot = pick_boot_params(dict(st.query_params))
anchor_date = boot.get("dayDate") or default_date

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": "你好！左邊係原版課表；呢度可以問 6–7 月時間表。"}
    ]

with st.sidebar:
    st.title("🤖 AI 問答")
    st.caption("中間係 GitHub 原版 UI；用 Streamlit Secrets 嘅 DeepSeek。")

    labels = [x[1] for x in day_opts]
    values = [x[0] for x in day_opts]
    idx = values.index(anchor_date) if anchor_date in values else 0
    picked = st.selectbox("AI 參考日期", labels, index=idx)
    anchor_date = values[labels.index(picked)]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    for p in ["今日 1A 第3節上咩？", "李老師今日行程", "6月16日有咩特別活動？"]:
        if st.button(p, use_container_width=True, key="q_" + p):
            st.session_state._pending_chat = p

    pending = st.session_state.pop("_pending_chat", None)
    user_q = st.chat_input("用中文問時間表…")
    question = pending or user_q

    if question:
        st.session_state.chat_messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("查詢中…"):
                try:
                    answer = ask_timetable(question, anchor_date)
                except Exception as e:
                    answer = f"❌ {e}"
                st.markdown(answer)
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
        if len(st.session_state.chat_messages) > 24:
            st.session_state.chat_messages = st.session_state.chat_messages[-24:]

    st.divider()
    st.markdown("**分享連結參數**（可貼去 Streamlit 網址）：")
    st.code(
        "tab=day&dayDate=2026-06-10&teacherDate=2026-06-10&teacherName=李"
        "&matrixMode=table&matrixClass=1A&matrixPeriod=p1",
        language="text",
    )
    st.link_button(
        "GitHub Pages 原版",
        "https://chilinbpscth.github.io/school-timetable-2026/"
        "?tab=day&dayDate=2026-06-10&teacherDate=2026-06-10&teacherName=%E6%9D%8E"
        "&matrixMode=table&matrixClass=1A&matrixPeriod=p1",
        use_container_width=True,
    )

try:
    ui_html = load_ui_html(dict(st.query_params))
except Exception as e:
    st.error(f"無法載入課表 UI：{e}")
    st.stop()

components.html(ui_html, height=1320, scrolling=True)