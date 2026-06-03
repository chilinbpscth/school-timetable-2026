from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data.json"

SLOT_LABELS = {
    "p1": "第1節",
    "p2": "第2節",
    "p3": "第3節",
    "p4": "第4節",
    "p5": "第5節",
    "p6": "第6節",
    "recess1": "小息1",
    "recess2": "小息2",
    "lunch": "午膳",
    "duty": "當值",
}
SLOT_ORDER_FULL = ["p1", "p2", "recess1", "p3", "recess2", "p4", "lunch", "p5", "p6", "duty"]
SLOT_ORDER_HALF = ["p1", "p2", "recess1", "p3", "p4", "duty"]
SLOT_ORDER_FRIDAY = ["p1", "p2", "recess1", "p3", "recess2", "p4", "lunch", "p5", "duty"]

DUTY_LABELS = {
    "recess1": "小息一",
    "recess1_half": "小息",
    "recess2": "小息二",
    "lunch_sup": "午膳各班",
    "lunch_recess": "午息",
    "dismissal": "放學",
}


@lru_cache(maxsize=1)
def load_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def find_day(data: dict, iso: str) -> dict | None:
    for d in data.get("days", []):
        if d.get("date") == iso:
            return d
    return None


def day_options(data: dict) -> list[tuple[str, str]]:
    out = []
    for d in data.get("days", []):
        label = d.get("label", d.get("date", ""))
        if d.get("type") == "half-day":
            label += "（半天）"
        else:
            label += "（全日）"
        out.append((d["date"], label))
    return out


def teacher_options(data: dict) -> list[tuple[str, str]]:
    out = []
    for t in data.get("teachers", []):
        short = t.get("short", "")
        no = str(t.get("no") or t.get("seq") or "").zfill(2)
        out.append((short, f"{no} {short}"))
    return out


def slot_order(day: dict) -> list[str]:
    if day.get("type") == "half-day":
        return SLOT_ORDER_HALF
    if day.get("weekday") == "五":
        return SLOT_ORDER_FRIDAY
    return SLOT_ORDER_FULL


def period_count(day: dict) -> int:
    return day.get("periodCount") or (6 if day.get("type") == "full-day" else 4)