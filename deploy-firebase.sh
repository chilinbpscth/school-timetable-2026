#!/usr/bin/env bash
# Deploy timetable site + chat API proxy to Firebase.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Building index.html from template + data.json"
python3 build.py

echo "==> Installing function dependencies"
(cd functions && npm install)

if [ ! -f functions/.env ]; then
  if [ -f scripts/sync-deepseek-env.sh ]; then
    echo "==> Syncing DEEPSEEK_API_KEY from school-management Streamlit secrets"
    bash scripts/sync-deepseek-env.sh || true
  fi
fi
if [ ! -f functions/.env ]; then
  echo "WARN: functions/.env not found."
  echo "      Run: bash scripts/sync-deepseek-env.sh"
  echo "      (reads ~/Desktop/school-management-system/.streamlit/secrets.toml)"
fi

echo "==> Deploying hosting + functions (asia-east1)"
echo "    Requires Blaze plan on the Firebase project."
firebase deploy --only hosting,functions

echo "Done."