#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="${AI_HEALTH_PROJECT_DIR:-$HOME/workbench/AH_web_development_assignment}"
WORKER_VENV="${AI_HEALTH_WORKER_VENV:-$HOME/.venvs/ai-health-worker}"
MODEL_DIR="$PROJECT_DIR/worker/models/pneumonia_ensemble_v1"
PLIST_PATH="$HOME/Library/LaunchAgents/com.ozcoding.ai-health-worker.plist"
WORKER_LOG="$HOME/Library/Logs/ai-health-worker.log"
WORKER_ERROR_LOG="$HOME/Library/Logs/ai-health-worker.err.log"
SERVICE_NAME="gui/$(id -u)/com.ozcoding.ai-health-worker"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

cd "$PROJECT_DIR"

if [[ ! -f "$MODEL_DIR/manifest.json" ]]; then
    echo "Prediction model is missing: $MODEL_DIR" >&2
    exit 1
fi

if ! command -v redis-server >/dev/null 2>&1; then
    brew install redis
fi
brew services start redis >/dev/null 2>&1 || brew services restart redis

for _ in {1..20}; do
    if redis-cli ping 2>/dev/null | grep -q PONG; then
        break
    fi
    sleep 1
done
redis-cli ping | grep -q PONG

uv python install 3.13
mkdir -p "$(dirname "$WORKER_VENV")"
if [[ ! -x "$WORKER_VENV/bin/python" ]]; then
    uv venv --python 3.13 "$WORKER_VENV"
fi
uv pip install \
    --python "$WORKER_VENV/bin/python" \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r "$PROJECT_DIR/worker/requirements.txt"

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ozcoding.ai-health-worker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${PROJECT_DIR}/scripts/run_prediction_worker.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>AI_HEALTH_PROJECT_DIR</key>
        <string>${PROJECT_DIR}</string>
        <key>AI_HEALTH_WORKER_PYTHON</key>
        <string>${WORKER_VENV}/bin/python</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>${WORKER_LOG}</string>
    <key>StandardErrorPath</key>
    <string>${WORKER_ERROR_LOG}</string>
</dict>
</plist>
PLIST

plutil -lint "$PLIST_PATH"
launchctl bootout "$SERVICE_NAME" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl enable "$SERVICE_NAME"
launchctl kickstart -k "$SERVICE_NAME"

echo "Prediction runtime installation completed."
