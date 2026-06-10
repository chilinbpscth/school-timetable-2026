from __future__ import annotations

import re

import streamlit as st
from openai import OpenAI

from timetable.context import build_chat_context

SYSTEM_PROMPT = """你是佛教志蓮小學 2026年6至7月時間表查詢助手。
只根據用戶提供的「時間表資料」回答，不可捏造課堂、當值或活動。
若資料中沒有答案，請明確說「資料中找不到」並建議用戶換日期或老師名再問。
可以根據「最近對話」理解追問，例如「咁第二日呢？」、「佢呢？」、「同一班呢？」。
用繁體中文（香港）簡潔回答，可用條列。老師名用簡稱（如李、符）。"""


def get_client() -> OpenAI:
    cfg = st.secrets.get("deepseek", {})
    api_key = (cfg.get("api_key") or "").strip()
    if not api_key or api_key.startswith("sk-your"):
        raise RuntimeError(
            "DeepSeek API key 未設定。請喺 Streamlit Cloud → App settings → Secrets "
            "貼上 [deepseek]（同校務系統 secrets.toml 一樣）。"
        )
    return OpenAI(
        api_key=api_key,
        base_url=cfg.get("base_url", "https://api.deepseek.com"),
    )


def get_model(kind: str = "read") -> str:
    cfg = st.secrets.get("deepseek", {})
    if kind == "write":
        return cfg.get("model_write") or cfg.get("model_pro") or cfg.get("model") or "deepseek-v4-pro"
    return cfg.get("model_read") or cfg.get("model") or "deepseek-v4-flash"


def choose_model_kind(
    user_question: str,
    *,
    context: str,
    history: list[dict[str, str]],
) -> str:
    query = "\n".join(
        [item["content"] for item in history if item["role"] == "user"] + [user_question]
    )
    complex_patterns = [
        r"比較|分析|建議|安排|搵.*時間|邊段時間|最空|最忙|撞|衝突|同時|統計",
        r"跨日|幾日|一星期|今個星期|下星期|連續|所有|全部|多位|幾位",
        r"如果|假設|可唔可以安排|適合|最佳|避開",
    ]
    explicit_pro = re.search(r"\bpro\b|準確|複雜|詳細", query, re.I)
    multi_constraint = len(re.findall(r"老師|班|日期|活動|當值|小息|午膳|放學", query)) >= 3
    long_context = len(context) > 12000
    followup_chain = len([item for item in history if item["role"] == "user"]) >= 2
    if (
        explicit_pro
        or any(re.search(pattern, query) for pattern in complex_patterns)
        or multi_constraint
        or long_context
        or followup_chain
    ):
        return "write"
    return "read"


def _clean_history(history: list[dict[str, str]] | None) -> list[dict[str, str]]:
    if not history:
        return []
    out: list[dict[str, str]] = []
    for item in history[-8:]:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            out.append({"role": role, "content": content[:1200]})
    return out


def ask_timetable(
    user_question: str,
    anchor_date: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    clean_history = _clean_history(history)
    context_query = "\n".join(
        [item["content"] for item in clean_history if item["role"] == "user"] + [user_question]
    )
    context = build_chat_context(context_query, anchor_date)
    model_kind = choose_model_kind(user_question, context=context, history=clean_history)
    model = get_model(model_kind)
    client = get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"【時間表資料】\n{context}",
        },
    ]
    if clean_history:
        messages.append(
            {
                "role": "user",
                "content": "【最近對話】\n"
                + "\n".join(
                    f"{'用戶' if item['role'] == 'user' else '助手'}：{item['content']}"
                    for item in clean_history
                ),
            }
        )
    messages.append({"role": "user", "content": f"【用戶最新問題】\n{user_question}"})
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
    )
    answer = (resp.choices[0].message.content or "").strip() or "（無回覆內容）"
    if model_kind == "write":
        return f"（已用 Pro 處理複雜查詢）\n{answer}"
    return answer
