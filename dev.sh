#!/usr/bin/env bash
# Runs the agent backend and the Next.js console together.
set -euo pipefail
cd "$(dirname "$0")"

[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
if [ -f .env ]; then set -a; . ./.env; set +a; fi

uvicorn backend.main:app --host 127.0.0.1 --port "${PORT:-8000}" &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null || true' EXIT

cd frontend-next
[ -d node_modules ] || npm install
AGENT_BASE_URL="http://127.0.0.1:${PORT:-8000}" npm run dev
