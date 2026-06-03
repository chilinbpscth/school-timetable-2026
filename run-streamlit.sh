#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .streamlit/secrets.toml ]; then
  echo "提示：複製 .streamlit/secrets.toml.example → .streamlit/secrets.toml 並填入 API key"
fi
python3 -m streamlit run app.py --server.port 8502