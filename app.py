"""佛教志蓮小學 — 6至7月時間表（Streamlit Cloud）

Deploy: https://share.streamlit.io → 揀 repo school-timetable-2026 → main file: app.py
Secrets: 同校務系統 [deepseek] 區塊（見 .streamlit/secrets.toml.example）
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from timetable.chat import ask_timetable
from timetable.data import day_options, load_data, teacher_options
from timetable.views import render_day_tab, render_teacher_schedule

st.set_page_config(
    page_title="志蓮小學 — 時間表查詢",
    page_icon="📅",
    layout="wide",
)

data = load_data()
meta = data.get("meta", {})
days = data.get("days", [])
day_opts = day_options(data)
teacher_opts = teacher_options(data)

if not days:
    st.error("data.json 無日程資料")
    st.stop()

default_date = date.today().isoformat()
if not any(d[0] == default_date for d in day_opts):
    default_date = day_opts[0][0]

if "day_date" not in st.session_state:
    st.session_state.day_date = default_date
if "teacher_date" not in st.session_state:
    st.session_state.teacher_date = default_date
if "teacher_name" not in st.session_state:
    st.session_state.teacher_name = teacher_opts[0][0] if teacher_opts else ""
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": "你好！我可以根據 6–7 月時間表答問題，直接輸入即可。"}
    ]

st.title("佛教志蓮小學 — 6 至 7 月時間表查詢")
st.caption(
    f"{meta.get('year', '')} 學年｜{meta.get('version', '')}｜共 {len(days)} 日有資料"
)

tab_day, tab_teacher, tab_chat = st.tabs(["📅 揀日子睇全日", "👤 揀老師", "💬 AI 問答"])

with tab_day:
    labels = [x[1] for x in day_opts]
    values = [x[0] for x in day_opts]
    idx = values.index(st.session_state.day_date) if st.session_state.day_date in values else 0
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        picked = st.selectbox("日期", labels, index=idx, key="day_select_label")
        st.session_state.day_date = values[labels.index(picked)]
    with c2:
        if st.button("← 上一日", use_container_width=True) and idx > 0:
            st.session_state.day_date = values[idx - 1]
            st.rerun()
    with c3:
        if st.button("下一日 →", use_container_width=True) and idx < len(values) - 1:
            st.session_state.day_date = values[idx + 1]
            st.rerun()
    render_day_tab(data, st.session_state.day_date)

with tab_teacher:
    t_labels = [x[1] for x in teacher_opts]
    t_values = [x[0] for x in teacher_opts]
    d_labels = [x[1] for x in day_opts]
    d_values = [x[0] for x in day_opts]
    tc1, tc2 = st.columns(2)
    with tc1:
        td = st.selectbox(
            "日期",
            d_labels,
            index=d_values.index(st.session_state.teacher_date)
            if st.session_state.teacher_date in d_values
            else 0,
            key="teacher_day_select",
        )
        st.session_state.teacher_date = d_values[d_labels.index(td)]
    with tc2:
        tn = st.selectbox(
            "老師",
            t_labels,
            index=t_values.index(st.session_state.teacher_name)
            if st.session_state.teacher_name in t_values
            else 0,
            key="teacher_name_select",
        )
        st.session_state.teacher_name = t_values[t_labels.index(tn)]
    day = next((d for d in days if d["date"] == st.session_state.teacher_date), None)
    if day:
        st.subheader(f"{day.get('label')} — 老師 {st.session_state.teacher_name}")
        render_teacher_schedule(day, st.session_state.teacher_name)

with tab_chat:
    st.caption("使用 Streamlit Secrets 嘅 DeepSeek API（同校務系統一樣設定）")
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompts = ["今日 1A 第3節上咩？", "李老師今日行程", "6月16日有咩特別活動？"]
    pcols = st.columns(len(prompts))
    for col, p in zip(pcols, prompts):
        with col:
            if st.button(p, use_container_width=True):
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
                    answer = ask_timetable(question, st.session_state.day_date)
                except Exception as e:
                    answer = f"❌ {e}"
                st.markdown(answer)
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
        if len(st.session_state.chat_messages) > 24:
            st.session_state.chat_messages = st.session_state.chat_messages[-24:]

with st.sidebar:
    st.markdown("### 說明")
    st.markdown(
        "- **靜態版**（GitHub Pages）：只睇表\n"
        "- **本 App**（Streamlit）：表 + AI 問答\n"
        "- API key 喺 Streamlit Cloud Secrets，唔使 Firebase Blaze"
    )
    st.markdown("### 快捷連結")
    st.link_button(
        "GitHub Pages 課表",
        "https://chilinbpscth.github.io/school-timetable-2026/",
        use_container_width=True,
    )