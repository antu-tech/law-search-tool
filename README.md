# Antu Legal Search

輕量級、可自托管的法律卷宗全文檢索與語意搜尋系統。律師客戶自行提供 OpenAI / Claude API Key，資料完全在地。

## 功能
- **PDF / Word 解析**：自動分段建立索引
- **語意搜尋**：基於 OpenAI Embedding 的向量檢索
- **關鍵字搜尋**：SQLite 輕量全文過濾
- **法律條文匹配**：AI 自動推薦適用法條
- **自帶 API Key**：每位用戶使用自己的 OpenAI / Claude Key，平台不儲存

## 快速開始

### 1. 克隆並啟動
```bash
cd law-search-tool
docker-compose up --build
```

### 2. 開啟瀏覽器
訪問 http://localhost:8000

### 3. 輸入 API Key
在「設定」頁面輸入你的 OpenAI / Claude / 兼容 API Key，即可開始上傳與搜尋。

## 技術棧
| 層級 | 技術 |
|------|------|
| 後端 | Python 3.11, FastAPI |
| 向量 | NumPy 輕量索引（零外部向量資料庫）|
| 文件 | PyMuPDF, python-docx |
| 儲存 | SQLite |
| 部署 | Docker Compose |

## API 概要
| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/documents` | 上傳 PDF/DOCX 並索引 |
| GET  | `/api/documents` | 列出已索引文件 |
| DELETE | `/api/documents/{id}` | 刪除文件 |
| GET  | `/api/search?q=...&mode=semantic` | 搜尋（semantic/keyword/hybrid）|
| GET  | `/api/legal-articles?q=...` | AI 法律條文匹配 |

## 第三方授權

本系統使用以下開源專案與公開資料：

- [mcp-taiwan-legal-db](https://github.com/lawchat-oss/mcp-taiwan-legal-db) — MIT License（程式碼）/ CC0 1.0（憲法法庭資料）
  - 資料來源：司法院裁判書系統、全國法規資料庫、司法院憲法法庭
- [FastAPI](https://fastapi.tiangolo.com/) — MIT License
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — AGPL / 商業授權
- [python-docx](https://github.com/python-openxml/python-docx) — MIT License
- [NumPy](https://numpy.org/) — BSD-3-Clause

裁判書與法規條文屬政府公開資料，依《著作權法》第 9 條不受著作權保護。

## 開發
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn src.api.main:app --reload
```
