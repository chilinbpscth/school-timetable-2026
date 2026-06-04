from __future__ import annotations

import streamlit as st
from openai import OpenAI

from timetable.context import build_chat_context

SYSTEM_PROMPT = """你是佛教志蓮小學 2026年6至7月時間表查詢助手。
只根據用戶提供的「時間表資料」回答，不可捏造課堂、當值或活動。
若資料中沒有答案，請明確說「資料中找不到」並建議用戶換日期或老師名再問。
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


def get_model() -> str:
    cfg = st.secrets.get("deepseek", {})
    return cfg.get("model_read") or cfg.get("model") or "deepseek-v4-flash"


def ask_timetable(user_question: str, anchor_date: str) -> str:
    context = build_chat_context(user_question, anchor_date)
    client = get_client()
    resp = client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"【時間表資料】\n{context}\n\n【用戶問題】\n{user_question}",
            },
        ],
        temperature=0.3,
        max_tokens=2048,
    )
    return (resp.choices[0].message.content or "").strip() or "（無回覆內容）"