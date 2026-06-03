#!/usr/bin/env bash
# Copy DeepSeek API key from school-management-system Streamlit secrets.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SECRETS="${SCHOOL_MGMT_SECRETS:-$HOME/Desktop/school-management-system/.streamlit/secrets.toml}"
OUT="$ROOT/functions/.env"

if [ ! -f "$SECRETS" ]; then
  echo "Missing secrets: $SECRETS" >&2
  exit 1
fi

python3 << PY
from pathlib import Path
import tomllib

secrets_path = Path("$SECRETS")
out_path = Path("$OUT")
data = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
key = (data.get("deepseek") or {}).get("api_key", "").strip()
if not key or key.startswith("sk-your"):
    raise SystemExit("No valid [deepseek].api_key in secrets.toml")
out_path.write_text(f"DEEPSEEK_API_KEY={key}\n", encoding="utf-8")
print(f"Wrote {out_path}")
PY