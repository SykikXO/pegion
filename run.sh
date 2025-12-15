#!/bin/bash
REPO_DIR="$(realpath .)"
cd "$REPO_DIR" || exit 1

restart_all() {
  echo "Update detected! Killing Python and restarting..."
  pkill -f "venv/bin/python.*main\.py" 2>/dev/null
  sleep 2
  exec ./run.sh "$@"  # Simple, works from repo root
}

while true; do
  echo "Checking for updates..."
  git fetch origin 2>/dev/null || { sleep 10; continue; }
  
  if [ "$(git rev-parse HEAD)" != "$(git rev-parse @{u})" ]; then
    git pull origin "$(git branch --show-current)"
    restart_all
  fi
  
  if ! pgrep -f "venv/bin/python.*main\.py" > /dev/null; then
    echo "Bot not running. Starting..."
    
    # Only install deps if requirements.txt changed
    REQ_HASH=$(md5sum requirements.txt | cut -d' ' -f1)
    CACHED_HASH=""
    [ -f .req_hash ] && CACHED_HASH=$(cat .req_hash)
    
    if [ "$REQ_HASH" != "$CACHED_HASH" ]; then
      echo "Requirements changed. Installing dependencies..."
      venv/bin/python -m pip install --upgrade pip -q
      venv/bin/python -m pip install -r requirements.txt -q
      echo "$REQ_HASH" > .req_hash
    fi
    
    echo "Starting bot..."
    nohup venv/bin/python main.py > bot.log 2>&1 &
  fi
  
  sleep 10
done
