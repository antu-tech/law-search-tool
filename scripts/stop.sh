#!/bin/bash
# Antu Legal Search — Stop Services
set -e

cd "$(dirname "$0")/.."

echo "停止 Antu Legal Search..."
docker-compose down

echo "服務已停止。"
