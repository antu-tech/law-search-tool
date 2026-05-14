# Harness.io 開發工作流指南

本文件說明如何在開發 `law-search-tool` 時，使用 Harness.io 建立完整的 CI/CD 工作流：從 Bitbucket 推送程式碼 → 自動測試 → 建置 Docker 映像檔 → 部署到 Docker 環境。

## 目錄
1. [架構概覽](#1-架構概覽)
2. [前置準備](#2-前置準備)
3. [設定 Bitbucket 連線](#3-設定-bitbucket-連線)
4. [CI Pipeline — 測試與建置](#4-ci-pipeline--測試與建置)
5. [CD Pipeline — 部署到 Docker](#5-cd-pipeline--部署到-docker)
6. [Trigger — 自動觸發](#6-trigger--自動觸發)
7. [Secrets 管理](#7-secrets-管理)
8. [Feature Flags（功能開關）](#8-feature-flags功能開關)
9. [常見問題](#9-常見問題)

---

## 1. 架構概覽

```
[開發者推送程式碼]
        │
        ▼
[Bitbucket main] ──► [Harness Trigger] ──► [CI Pipeline]
                                                │
                    ┌───────────────────────────┘
                    ▼
            [Run pytest] ──► [Build Docker Image] ──► [Push to Registry]
                                                                │
                    ┌───────────────────────────────────────────┘
                    ▼
            [CD Pipeline] ──► [SSH to Docker Host] ──► [docker-compose up]
                                                                │
                    ┌───────────────────────────────────────────┘
                    ▼
            [Law Search Tool Running]
```

---

## 2. 前置準備

- Harness.io 已透過 Docker 在本機或伺服器運行
- Bitbucket 倉庫 `law-search-tool` 已建立
- Docker Registry 帳號（Docker Hub、AWS ECR、GCR 皆可）
- 一台用於部署的 Docker Host（可以是同一台機器或遠端 VM）

---

## 3. 設定 Bitbucket 連線

### 步驟 A：在 Harness 建立 Connector
1. 登入 Harness，進入 **Project Settings > Connectors**
2. 點擊 **New Connector > Code Repositories > Bitbucket**
3. 填寫名稱：`bitbucket-law-search`
4. **Connection Type**: `Repo`
5. **URL Type**: `Repository`
6. **Repository URL**: `https://bitbucket.org/mlpfim/law-search-tool.git`
7. **Authentication**:
   - 選擇 **Username and Password**
   - Username: 你的 Bitbucket 用戶名
   - Password: **App Password**（非登入密碼，需在 Bitbucket Settings > App Passwords 建立）
8. 測試連線並儲存

### 步驟 B：設定 Git Experience
1. 進入 **Project Settings > Default Settings > Git Experience**
2. 開啟 **Allow Harness to store your Harness entities in Git**
3. 選擇 `bitbucket-law-search` 作為預設連線器

---

## 4. CI Pipeline — 測試與建置

### 步驟 A：匯入 Pipeline
1. 進入 **Pipelines > New Pipeline**
2. 選擇 **Import From Git** 或手動建立
3. 將 `config/harness/ci_pipeline.yml` 的 YAML 貼上
4. 修改以下變數：
   - `<+pipeline.variables.DOCKER_REGISTRY>` → 你的 Docker Hub 用戶名（如 `docker.io/mlpfim`）

### 步驟 B：Pipeline 說明
| Step | 目的 |
|------|------|
| **Clone Codebase** | 從 Bitbucket 拉取最新程式碼 |
| **Install Dependencies** | `pip install -r requirements.txt` |
| **Run Tests** | `pytest tests/ -v`（必須通過才能繼續）|
| **Build and Push Image** | 建置 Docker image 並推送到 Registry |

### 步驟 C：執行
- 手動執行：點擊 **Run Pipeline**，輸入 `DOCKER_REGISTRY`
- 自動執行：見下方 Trigger 設定

---

## 5. CD Pipeline — 部署到 Docker

### 步驟 A：建立 Infrastructure
1. 進入 **Environments > New Environment**
   - 名稱：`dev`
   - 類型：`Pre-Production`
2. 在環境內新增 **Infrastructure Definition**
   - 類型：`SSH`
   - 名稱：`dockerhost`
   - 選擇或建立 SSH Credential（見第 7 節）
   - Host：你的 Docker Host IP 或 `host.docker.internal`

### 步驟 B：建立 Service
1. 進入 **Services > New Service**
   - 名稱：`lawsearchtool`
   - 可選：上傳 `docker-compose.yml` 作為 Artifact

### 步驟 C：匯入 CD Pipeline
1. 將 `config/harness/cd_pipeline.yml` 匯入
2. 修改變數：
   - `DOCKER_REGISTRY` → `docker.io/mlpfim`
   - `DOCKER_HOST` → 部署目標 IP
   - `DOCKER_HOST_USER` → SSH 使用者（如 `ubuntu` 或 `root`）

### 部署流程
```bash
# Harness 會在 Delegate 上執行以下動作
ssh -i /path/to/ssh_key user@docker_host \
  "cd /opt/law-search-tool && \
   docker pull docker.io/mlpfim/law-search-tool:latest && \
   docker-compose down && \
   docker-compose up -d"
```

---

## 6. Trigger — 自動觸發

### Webhook Trigger（推薦）
1. 在 Harness Pipeline 頁面點擊 **Triggers > New Trigger > Webhook**
2. 選擇 **Custom** 類型
3. 匯入 `config/harness/trigger.yml`，或手動設定：
   - **Payload Condition**: `push.changes.0.new.name` Equals `main`
   - **Pipeline**: 選擇 `law-search-tool-ci`
4. 儲存後，Harness 會產生一個 **Webhook URL**
5. 到 **Bitbucket > Repository Settings > Webhooks**，新增 Webhook：
   - URL: `<Harness Webhook URL>`
   - Triggers: **Repository push**

### 效果
每次 `git push origin main`，自動：
1. 執行 pytest（失敗則中止）
2. 建置並推送新 Docker image
3. （可選鏈接 CD）自動部署到 Docker Host

---

## 7. Secrets 管理

所有敏感資訊都應存入 Harness Secrets，**絕對不要寫死在 YAML 中**。

| Secret 名稱 | 內容 | 用途 |
|-------------|------|------|
| `kimi_api_key` | `sk-...` | 開發測試時呼叫 Kimi API |
| `bitbucket_app_password` | Bitbucket App Password | Git 連線 |
| `docker_hub_password` | Docker Hub Token | 推送映像檔 |
| `docker_host_ssh_key` | SSH Private Key | CD 部署到 Docker Host |
| `docker_host_ssh_user` | `ubuntu` | SSH 使用者名稱 |

### 在 Pipeline 中引用
```yaml
# Secret
<+secrets.getValue("kimi_api_key")>

# Variable
<+pipeline.variables.DOCKER_REGISTRY>
```

---

## 8. Feature Flags（功能開關）

在開發新功能時，使用 Harness Feature Flags 控制上線，避免影響律師客戶。

### 範例：控制 AI 搜尋開關
1. 進入 **Feature Flags > New Feature Flag**
   - 名稱：`enable_ai_search`
   - 類型：`Boolean`
   - 預設：`false`
2. 在 `src/api/main.py` 中整合 SDK（可選，未來擴展）：

```python
# 未來擴展：整合 Harness Feature Flag SDK
# from harness.featureflag import CfClient
# client = CfClient("<SDK_KEY>")
# if client.bool_evaluation("enable_ai_search", target, False):
#     results = await semantic_search(...)
# else:
#     results = keyword_search(...)
```

### 使用情境
- **開發階段**：`enable_ai_search = false`，僅用關鍵字搜尋，節省 Kimi API 費用
- **灰度測試**：對 10% 用戶開啟 AI 搜尋
- **正式上線**：全面開啟

---

## 9. 常見問題

### Q1: Harness Delegate 無法連線到 Docker Host
**解決**：確認兩者在同一 Docker network，或 Delegate 能透過 SSH/HTTP 存取 Docker Host。

```bash
# 將 law-search-tool 加入 Harness 網路
docker network connect harness-shared-net law-search-tool
```

### Q2: pytest 在 Harness CI 中失敗
**解決**：CI YAML 中使用 `python:3.11-slim` 映像檔，確認 `requirements.txt` 包含 `pytest-asyncio`。

### Q3: Docker build 成功但 push 失敗
**解決**：檢查 Docker Registry Connector 設定，確認使用 **Docker Hub Access Token** 而非登入密碼。

### Q4: 如何只部署特定分支？
**解決**：在 Trigger 的 Payload Condition 中增加：
```yaml
- key: push.changes.0.new.name
  operator: Equals
  value: main
```

### Q5: 如何在本地測試 Harness Pipeline？
**解決**：使用 Harness Local Runner（需安裝 `harness-delegate`），或在 Docker Desktop 中直接執行：
```bash
docker build -t law-search-tool:test . && pytest tests/
```

---

## 附錄：完整開發工作流

```bash
# 1. 本地開發
git checkout -b feature/semantic-search
# ... 修改程式碼 ...
pytest tests/ -v

# 2. 提交並推送
git add .
git commit -m "feat: add hybrid search mode"
git push origin feature/semantic-search

# 3. 開 PR（Bitbucket）
# → Harness Trigger 可選擇在 PR 時執行 CI

# 4. Merge 到 main
# → Harness Webhook Trigger 自動啟動 CI/CD
# → pytest → build → push → deploy

# 5. 驗證部署
 curl http://docker-host:8000/api/documents
```
