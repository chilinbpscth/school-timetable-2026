from __future__ import annotations

import re
from datetime import date

from timetable.data import (
    DUTY_LABELS,
    SLOT_LABELS,
    find_day,
    load_data,
    period_count,
)

_RE_ISO = re.compile(r"2026-\d{2}-\d{2}")


def _escape_short(name: str) -> str:
    return re.escape(name or "")


def parse_dates_from_query(q: str, data: dict, anchor_date: str) -> list[str]:
    found: set[str] = set()
    for m in _RE_ISO.finditer(q):
        found.add(m.group(0))

    for d in data.get("days", []):
        label = d.get("label", "")
        m1 = re.search(r"(\d+)月(\d+)日", label)
        if m1:
            month, day = int(m1.group(1)), int(m1.group(2))
            patterns = [
                rf"{month}\s*月\s*{day}\s*日",
                rf"{month}\s*/\s*{day}",
                rf"\b{month}-{day}\b",
            ]
            if any(re.search(p, q) for p in patterns):
                found.add(d["date"])

    today = date.today().isoformat()
    if re.search(r"今日|今天|今個", q):
        if find_day(data, today):
            found.add(today)
        elif anchor_date:
            found.add(anchor_date)

    days = data.get("days", [])
    if anchor_date:
        idx = next((i for i, d in enumerate(days) if d["date"] == anchor_date), -1)
        if idx >= 0:
            if re.search(r"明日|明天", q) and idx < len(days) - 1:
                found.add(days[idx + 1]["date"])
            if re.search(r"後日", q) and idx < len(days) - 2:
                found.add(days[idx + 2]["date"])

    for d in days:
        short_label = re.sub(r"\([^)]*\)", "", d.get("label", "")).strip()
        if short_label and short_label in q:
            found.add(d["date"])
        wd = d.get("weekday")
        if wd and re.search(rf"星期{wd}|週{wd}|周{wd}", q) and anchor_date:
            idx = next((i for i, x in enumerate(days) if x["date"] == anchor_date), -1)
            if idx >= 0:
                for i in range(max(0, idx - 7), min(len(days), idx + 8)):
                    if days[i].get("weekday") == wd:
                        found.add(days[i]["date"])

    return list(found)


def parse_teachers_from_query(q: str, data: dict) -> list[str]:
    hits: list[str] = []
    for t in data.get("teachers", []):
        s = t.get("short", "")
        if not s:
            continue
        if f"{s}老師" in q or f"{s}師" in q or f"{s}主任" in q:
            hits.append(s)
        elif re.search(rf"(^|[^\u4e00-\u9fff]){_escape_short(s)}([^\u4e00-\u9fff]|$)", q):
            hits.append(s)
    return list(dict.fromkeys(hits))


def parse_classes_from_query(q: str, data: dict) -> list[str]:
    return [c for c in data.get("classes", []) if c in q]


def compact_duties(duties: dict | None) -> str:
    if not duties:
        return ""
    parts = []
    for key, label in DUTY_LABELS.items():
        items = duties.get(key) or []
        if not items:
            continue
        row = []
        for x in items:
            val = x.get("value") or ""
            lab = (x.get("label") or "").replace("\n", " ")
            row.append(f"{val}({lab})" if lab else val)
        parts.append(f"{label}: {'; '.join(filter(None, row))}")
    return "\n".join(parts)


def compact_teacher_day(day: dict, short: str) -> str:
    ts = (day.get("teacherSchedules") or {}).get(short)
    if not ts:
        return f"老師 {short}: 當日無資料"
    lines = [f"老師 {short}" + (f"（班主任 {ts['homeroom']}）" if ts.get("homeroom") else "") + ":"]
    for k, v in (ts.get("slots") or {}).items():
        v = (v or "").strip()
        if v:
            lines.append(f"  {SLOT_LABELS.get(k, k)}: {v}")
    return "\n".join(lines)


def compact_class_day(day: dict, classes: list[str], all_classes: list[str]) -> str:
    use = classes if classes else all_classes
    n_p = period_count(day)
    lines = []
    for c in use:
        sched = (day.get("classSchedules") or {}).get(c) or {}
        cells = []
        for i in range(1, n_p + 1):
            v = (sched.get(f"p{i}") or "").strip()
            if v:
                cells.append(f"p{i}={v}")
        if cells:
            lines.append(f"{c}: {', '.join(cells)}")
    return "\n".join(lines)


def serialize_day_for_chat(
    day: dict,
    *,
    teachers: list[str],
    classes: list[str],
    all_classes: list[str],
    include_class_matrix: bool,
    include_all_teachers: bool,
) -> str:
    lines = [
        f"【{day.get('label')} {day.get('date')}】"
        f"{'全日' if day.get('type') == 'full-day' else '半天'}（星期{day.get('weekday', '?')}）"
    ]
    if day.get("activities"):
        lines.append("當日活動:\n" + day["activities"])
    md = day.get("morningDuty")
    if md:
        lines.append("早上特別當值: " + (md.get("title") or ""))
        for s in md.get("stations") or []:
            lines.append(f"  {s.get('time', '')} {s.get('location', '')} → {s.get('people', '')}")
    duty_text = compact_duties(day.get("duties"))
    if duty_text:
        lines.append("其他當值:\n" + duty_text)
    if teachers:
        for t in teachers:
            lines.append(compact_teacher_day(day, t))
    elif include_all_teachers:
        for t in list((day.get("teacherSchedules") or {}).keys())[:8]:
            lines.append(compact_teacher_day(day, t))
    if classes:
        lines.append("班別課表:\n" + compact_class_day(day, classes, all_classes))
    elif include_class_matrix:
        lines.append("班別課表:\n" + compact_class_day(day, [], all_classes))
    return "\n".join(lines)


def build_chat_context(query: str, anchor_date: str) -> str:
    data = load_data()
    dates = parse_dates_from_query(query, data, anchor_date)
    teachers = parse_teachers_from_query(query, data)
    classes = parse_classes_from_query(query, data)

    days = data.get("days", [])
    day_list = [find_day(data, d) for d in dates]
    day_list = [d for d in day_list if d]

    if not day_list:
        anchor = anchor_date or (days[0]["date"] if days else "")
        idx = next((i for i, d in enumerate(days) if d["date"] == anchor), -1)
        if idx >= 0:
            day_list = days[max(0, idx - 1) : idx + 2]
        else:
            day_list = days[:2]

    day_list = day_list[:5]
    all_classes = data.get("classes", [])
    include_class_matrix = not classes and not teachers and len(day_list) <= 2
    include_all_teachers = not teachers and len(day_list) == 1 and re.search(
        r"老師|教師|代課|行程", query
    )

    blocks = [
        serialize_day_for_chat(
            d,
            teachers=teachers,
            classes=classes,
            all_classes=all_classes,
            include_class_matrix=include_class_matrix,
            include_all_teachers=include_all_teachers,
        )
        for d in day_list
    ]

    teacher_list = "、".join(
        f"{t.get('short')}{'(' + t['homeroom'] + ')' if t.get('homeroom') else ''}"
        for t in data.get("teachers", [])
    )

    return "\n".join(
        [
            f"學校: {data.get('meta', {}).get('schoolName', '')}",
            f"學年: {data.get('meta', {}).get('year', '')}｜版本: {data.get('meta', {}).get('version', '')}",
            f"涵蓋日期: {days[0].get('label', '')} 至 {days[-1].get('label', '')}" if days else "",
            f"老師簡稱: {teacher_list}",
            "",
            "--- 以下為查詢相關日子資料 ---",
            "\n\n".join(blocks),
        ]
    )