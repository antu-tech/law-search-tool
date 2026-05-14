# Antu Legal Search

輕量級、可自托管的法律卷宗全文檢索與語意搜尋系統。律師客戶自行提供 OpenAI / Claude API Key，資料完全在地。

---

## 給律師：快速安裝（無需寫程式）

### 事前準備

只需安裝 **Docker Desktop**：
- [macOS 下載](https://docs.docker.com/desktop/install/mac-install/)
- [Windows 下載](https://docs.docker.com/desktop/install/windows-install/)

安裝後開啟 Docker Desktop，確保左下角顯示綠燈（Engine running）。

### 一鍵安裝

開啟終端機（Terminal / 命令提示字元），貼上這一行：

```bash
curl -fsSL https://raw.githubusercontent.com/mlpfim0502/law-search-tool/main/scripts/install.sh | bash
```

安裝完成後，開啟瀏覽器訪問 **http://localhost:8000**。

### 輸入 API Key

1. 點選左側「設定」
2. 輸入你的 OpenAI / Claude / Kimi API Key
3. 開始使用「卷宗搜尋」上傳 PDF 或 Word 文件

> **注意**：API Key 只存在你的電腦記憶體中，不會傳送到任何第三方伺服器。

### 日常操作

| 指令 | 說明 |
|------|------|
| `./scripts/start.sh` | 啟動服務 |
| `./scripts/stop.sh` | 停止服務 |
| `./scripts/update.sh` | 更新到最新版 |

> 所有資料（上傳的文件、索引資料庫）都存放在安裝目錄的 `data/` 與 `uploads/` 中。

---

## 給開發者

### 本地開發

```bash
git clone https://github.com/mlpfim0502/law-search-tool.git
cd law-search-tool
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn src.api.main:app --reload
```

### Docker 開發

```bash
docker-compose up --build
```

---

## 功能

- **PDF / Word 解析**：自動分段建立索引
- **語意搜尋**：基於 OpenAI Embedding 的向量檢索
- **關鍵字搜尋**：SQLite 輕量全文過濾
- **法律條文匹配**：AI 自動推薦適用法條
- **法規查詢**：全國法規資料庫 11,700+ 部法規
- **裁判書搜尋**：司法院裁判書系統
- **憲法法庭**：大法官解釋（釋字）與憲判字
- **自帶 API Key**：每位用戶使用自己的 Key，平台不儲存

---

## 技術棧

| 層級 | 技術 |
|------|------|
| 後端 | Python 3.11, FastAPI |
| 向量 | NumPy 輕量索引（零外部向量資料庫）|
| 文件 | PyMuPDF, python-docx |
| 儲存 | SQLite |
| 部署 | Docker Compose |

---

## 第三方授權

本系統使用以下開源專案與公開資料：

- [mcp-taiwan-legal-db](https://github.com/lawchat-oss/mcp-taiwan-legal-db) — MIT License（程式碼）/ CC0 1.0（憲法法庭資料）
  - 資料來源：司法院裁判書系統、全國法規資料庫、司法院憲法法庭
- [FastAPI](https://fastapi.tiangolo.com/) — MIT License
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — AGPL / 商業授權
- [python-docx](https://github.com/python-openxml/python-docx) — MIT License
- [NumPy](https://numpy.org/) — BSD-3-Clause

裁判書與法規條文屬政府公開資料，依《著作權法》第 9 條不受著作權保護。
