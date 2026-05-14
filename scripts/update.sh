#!/bin/bash
# Antu Legal Search — Update to Latest Version
set -e

cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}檢查更新...${NC}"

git fetch origin main
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
  echo -e "${GREEN}✓ 已經是最新版本${NC}"
  exit 0
fi

echo -e "${YELLOW}發現新版本，正在更新...${NC}"

echo "[1/3] 備份現有設定..."
if [ -f ".env" ]; then
  cp .env .env.backup
fi

echo "[2/3] 拉取最新程式碼..."
git pull origin main

echo "[3/3] 重建並啟動服務..."
docker-compose down
docker-compose up --build -d

echo ""
echo -e "${GREEN}✓ 更新完成！${NC}"
echo ""
echo "開啟瀏覽器訪問：http://localhost:8000"
echo ""
