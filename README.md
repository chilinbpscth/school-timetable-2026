# 示範小學 — 6至7月時間表查詢 Demo

互動式時間表工具 demo，使用已匿名化及重組的示範資料。

支援**日期課表**、**老師個人行程** 同 **AI 自然語言查詢**（DeepSeek）。

**即時預覽（靜態版）**：<br>
https://raw.githack.com/your-org/school-timetable-2026/demo-anonymized/index.html
（或 clone 後本地 `python3 -m http.server 8765` 開 http://localhost:8765/index.html）

## 主要功能

- 📅 **揀日子睇全日**：每節課表、當值（小息/午膳/放學）、特別活動、早上特別當值、鐘聲時間表
- 👤 **揀老師**：老師簡稱搜尋，顯示班主任 + 每節擔任工作（包括跨班數遊、LAMK 等）
- 🤖 **AI 查詢**：用自然語言提問，例如：
  - 「T01 老師 6 月 12 日有幾多堂？」
  - 「6月23日 5B 午膳邊個當值？」
  - 「後日 4A 有冇特別活動？」
- 支援分享連結（URL 帶參數，可直接開特定日子/老師/AI 問題）
- 全日 / 半天 自動適配（星期五特別安排）

## 技術架構

- **靜態版**：單一 `index.html`（template.html + data.json 經 build.py 嵌入），純前端 JS，適合 GitHub Pages / Firebase Hosting 直接 host。
- **Streamlit 版**：`app.py` 使用 `st.components.v1.html` 完整嵌入同一個 UI，負責 secrets 管理同 AI 後端呼叫。
- **AI**：使用 DeepSeek（OpenAI 相容 API），`timetable/context.py` 會智能抽取相關日子、老師、班別、當值資料，控制 token 數量。
- **資料**：`data.json` 為單一事實來源（21 日，22 班，48 位匿名化老師代號）。
- **更新流程**：手動維護 data.json → `python3 build.py`
- **可選後端**：Firebase Cloud Functions 提供 `/api/chat` proxy（避免前端暴露 key）。

## 本地運行

### 1. 靜態 HTML 預覽（最快，無需 key）

```bash
cd school-timetable-2026

# 方法一：Python
python3 -m http.server 8765
# 開瀏覽器 http://localhost:8765/index.html

# 方法二：npx（較好）
npx --yes http-server -p 8765 -c-1 .
```

### 2. Streamlit 版（完整體驗 + AI）

```bash
cd school-timetable-2026

# 第一次設定 secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# 用文字編輯器開啟，填入 DeepSeek API key

./run-streamlit.sh
# 預設開在 http://localhost:8502
```

`requirements.txt` 已包含 `streamlit` 及 `openai`（用作 DeepSeek client）。

## 更新時間表資料

1. 主要直接編輯 `data.json`（或用 parser.py 從學校 docx 重新抽取）。
2. 改完後執行：
   ```bash
   python3 build.py
   ```
3. 測試靜態版同 Streamlit 版。
4. Commit + push。

（parser.py 只保留作原型參考；demo 分支不應用於還原真實資料。）

## Deploy 到 Streamlit Community Cloud

1. 確保最新 code 已 push 到 GitHub（呢個 repo）。
2. 前往 [https://share.streamlit.io/](https://share.streamlit.io/)
3. 用擁有此 GitHub repo 權限的帳號登入。
4. **New app** → 選擇 "From existing repo" → 揀你的 demo repo
5. Branch 選 `demo-anonymized`
6. Main file path 填 `app.py`
7. **Deploy**

### 設定 Secrets（必須）

部署後或在 "App settings" → **Secrets** 加入以下內容：

```toml
[deepseek]
api_key = "sk-your-deepseek-api-key-here"
base_url = "https://api.deepseek.com"
model_read = "deepseek-v4-flash"
# model_write = "deepseek-v4-pro"   # 如需要
```

儲存後按 **Reboot app**。

Streamlit Cloud 會自動根據 `requirements.txt` 安裝依賴。

## 可選：Firebase Hosting + Functions

```bash
./deploy-firebase.sh
```

需要：
- Firebase CLI 已登入
- 對應 project（.firebaserc 內）
- `functions/.env` 有 `DEEPSEEK_API_KEY`
- Blaze 付費計劃（functions 需要）

## 檔案結構

```
school-timetable-2026/
├── app.py                 # Streamlit 入口
├── build.py               # 把 data.json 嵌入 index.html
├── data.json              # 核心時間表資料
├── index.html             # 靜態完整版（已 build）
├── template.html          # 靜態 UI 模板
├── parser.py              # docx → data.json（一次性）
├── requirements.txt
├── run-streamlit.sh
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── timetable/
│   ├── __init__.py
│   ├── chat.py            # AI 呼叫
│   ├── context.py         # 智能 context 組裝
│   ├── data.py            # 資料載入 + helper
│   └── embed.py           # Streamlit 嵌入 HTML 邏輯
├── functions/             # Firebase Cloud Functions（chat proxy）
└── README.md
```

## 注意事項

- AI 只根據 `data.json` 內資料回答，不會捏造。
- 無 key 時 Streamlit 會顯示清楚錯誤提示。
- 靜態版 index.html 可直接用 `<iframe>` 或 GitHub Pages 嵌入。

## 貢獻 / 維護

有新日子或改動，請更新 `data.json` 後 rebuild 再 push。

---

如有問題或想加功能，歡迎開 Issue 或直接聯絡維護者。

（本 README 由 Grok 協助生成）
