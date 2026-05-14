#!/bin/bash
# Antu Legal Search — Start Services
set -e

cd "$(dirname "$0")/.."

echo "啟動 Antu Legal Search..."
docker-compose up -d

echo ""
echo "服務已啟動：http://localhost:8000"
