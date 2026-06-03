from __future__ import annotations

import pandas as pd
import streamlit as st

from timetable.data import DUTY_LABELS, SLOT_LABELS, find_day, period_count, slot_order


def render_day_banner(day: dict) -> None:
    kind = "全日" if day.get("type") == "full-day" else "半天"
    st.subheader(f"{day.get('label')} · {kind}")


def render_activities(day: dict) -> None:
    text = (day.get("activities") or "").strip()
    if not text:
        st.info("當日無特別活動。")
        return
    st.markdown("#### 當日活動")
    for line in text.split("\n"):
        line = line.strip()
        if line:
            st.markdown(f"- {line}")


def render_duties(day: dict) -> None:
    duties = day.get("duties") or {}
    st.markdown("#### 其他當值")
    any_row = False
    for key, title in DUTY_LABELS.items():
        items = duties.get(key) or []
        if not items:
            continue
        any_row = True
        st.markdown(f"**{title}**")
        for x in items:
            lab = (x.get("label") or "").replace("\n", " · ")
            st.markdown(f"- {x.get('value', '')} — {lab}")
    if not any_row:
        st.caption("當日無其他當值資料")


def render_class_matrix(day: dict, classes: list[str]) -> None:
    n_p = period_count(day)
    rows = []
    for c in classes:
        sched = (day.get("classSchedules") or {}).get(c) or {}
        row = {"班別": c}
        for i in range(1, n_p + 1):
            row[f"第{i}節"] = sched.get(f"p{i}") or "—"
        rows.append(row)
    st.markdown("#### 班別總表")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_teacher_schedule(day: dict, short: str) -> None:
    ts = (day.get("teacherSchedules") or {}).get(short)
    if not ts:
        st.warning("當日無此老師資料")
        return
    rows = []
    for key in slot_order(day):
        val = ((ts.get("slots") or {}).get(key) or "").strip()
        if val:
            rows.append({"時段": SLOT_LABELS.get(key, key), "安排": val})
    if ts.get("homeroom"):
        st.caption(f"班主任：{ts['homeroom']}")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_day_tab(data: dict, day_date: str) -> str:
    day = find_day(data, day_date)
    if not day:
        st.error("找不到該日資料")
        return day_date
    render_day_banner(day)
    render_activities(day)
    render_duties(day)
    render_class_matrix(day, data.get("classes", []))
    return day_date