"""佛教志蓮小學 — 6至7月時間表（Streamlit：只顯示 GitHub 原版 UI，暫無 AI）"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from timetable.embed import load_ui_html

st.set_page_config(
    page_title="佛教志蓮小學 — 時間表查詢",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
  [data-testid="stSidebar"] { display: none; }
  header[data-testid="stHeader"] { display: none; }
  div[data-testid="stMain"] > div.block-container {
    padding: 0;
    max-width: 100%;
  }
  iframe { border: none !important; }
</style>
""",
    unsafe_allow_html=True,
)

try:
    ui_html = load_ui_html()
except Exception as e:
    st.error(f"無法載入課表：{e}")
    st.stop()

components.html(ui_html, height=1400, scrolling=True)