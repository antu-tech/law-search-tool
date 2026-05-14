#!/bin/bash
set -e

# =============================================================================
# Antu Legal Search — One-Line Installer for Lawyers
# =============================================================================
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/mlpfim0502/law-search-tool/main/scripts/install.sh | bash
#
# macOS 用戶推薦使用 .dmg 圖形介面安裝：
#   https://github.com/mlpfim0502/law-search-tool/releases
# =============================================================================

REPO_URL="https://github.com/mlpfim0502/law-search-tool.git"
INSTALL_DIR="${ANTU_INSTALL_DIR:-$HOME/antu-legal-search}"
PORT="${LAW_SEARCH_PORT:-8000}"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
  echo ""
  echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║                                                              ║${NC}"
  echo -e "${BLUE}║${NC}           Antu Legal Search 安裝程式                        ${BLUE}║${NC}"
  echo -e "${BLUE}║${NC}           輕量級法律搜尋系統                                  ${BLUE}║${NC}"
  echo -e "${BLUE}║                                                              ║${NC}"
  echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
  echo ""
}

check_prerequisites() {
  echo -e "${BLUE}[1/5]${NC} 檢查必要軟體..."

  if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker 未安裝${NC}"
    echo ""
    echo "請先安裝 Docker Desktop："
    echo "  macOS: https://docs.docker.com/desktop/install/mac-install/"
    echo "  Windows: https://docs.docker.com/desktop/install/windows-install/"
    echo ""
    exit 1
  fi

  if ! command -v git &> /dev/null; then
    echo -e "${RED}✗ Git 未安裝${NC}"
    echo ""
    echo "請先安裝 Git："
    echo "  macOS: brew install git    (或從 https://git-scm.com/download/mac 下載)"
    echo "  Windows: https://git-scm.com/download/win"
    echo ""
    exit 1
  fi

  echo -e "${GREEN}✓${NC} Docker 與 Git 已就緒"
}

clone_repo() {
  echo -e "${BLUE}[2/5]${NC} 下載最新版本..."

  if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${YELLOW}⚠ 目錄已存在，執行更新...${NC}"
    cd "$INSTALL_DIR"
    git pull origin main
  else
    rm -rf "$INSTALL_DIR"
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
  fi

  echo -e "${GREEN}✓${NC} 程式碼已就位"
}

setup_environment() {
  echo -e "${BLUE}[3/5]${NC} 設定環境..."

  cd "$INSTALL_DIR"

  # Create data directories
  mkdir -p data uploads

  # Create .env if not exists
  if [ ! -f ".env" ]; then
    cat > .env <<EOF
# Antu Legal Search 環境設定
# 如需使用 Kimi API，請取消下行註解並填入 Kimi Base URL
# OPENAI_BASE_URL=https://api.moonshot.cn/v1

# 服務埠號（預設 8000）
LAW_SEARCH_PORT=8000
EOF
  fi

  echo -e "${GREEN}✓${NC} 環境設定完成"
}

start_services() {
  echo -e "${BLUE}[4/5]${NC} 啟動服務（首次需要幾分鐘下載必要元件）..."

  cd "$INSTALL_DIR"
  docker-compose up --build -d

  echo -e "${GREEN}✓${NC} 服務已啟動"
}

print_success() {
  echo ""
  echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║                                                              ║${NC}"
  echo -e "${GREEN}║${NC}              安裝成功！                                       ${GREEN}║${NC}"
  echo -e "${GREEN}║                                                              ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  開啟瀏覽器訪問：${BLUE}http://localhost:${PORT}${NC}"
  echo ""
  echo -e "  後續操作（在終端機執行）："
  echo ""
  echo -e "    ${YELLOW}cd ${INSTALL_DIR}${NC}"
  echo -e "    ${YELLOW}./scripts/start.sh${NC}     # 啟動服務"
  echo -e "    ${YELLOW}./scripts/stop.sh${NC}      # 停止服務"
  echo -e "    ${YELLOW}./scripts/update.sh${NC}    # 更新到最新版"
  echo ""
  echo -e "  設定檔位置：${YELLOW}${INSTALL_DIR}/.env${NC}"
  echo ""
}

# =============================================================================
# Main
# =============================================================================
print_header
check_prerequisites
clone_repo
setup_environment
start_services
print_success
