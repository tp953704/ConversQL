# ConversQL 

這是一個基於 FastAPI 的應用程式，它利用 AI 代理（由 Ollama 和 LangChain 提供支援）透過「方法性對話協議（Methodical Conversation Protocol, MCP）」與 Oracle 資料庫進行互動。

使用者可以透過一個簡單的 API 端點，使用自然語言來查詢資料庫。

## ✨ 功能

-   **自然語言查詢**: 提供 `/api/ai/query` 端點，讓使用者可以用自然語言下達指令。
-   **AI 代理**: 使用 LangChain 和 LangGraph 建構的 AI 代理，能夠理解使用者意圖並使用工具與資料庫互動。
-   **Oracle 資料庫工具**:
    -   `get_table_ddl`: 獲取指定資料表的 DDL（資料定義語言）。
    -   `execute_select_query`: 安全地執行 `SELECT` 查詢。
-   **容器化**: 提供 `Dockerfile`，方便使用 Docker 進行部署。
-   **彈性設定**: 所有設定（如資料庫連線、Ollama 服務位址）皆透過 `.env` 檔案進行管理，與程式碼分離。

## 🏗️ 架構

本專案主要由兩個部分組成：

1.  **`api_optimized_api.py` (FastAPI 前端)**:
    -   負責接收來自使用者的 HTTP 請求。
    -   初始化 AI 代理（Agent）。
    -   將使用者的自然語言查詢傳遞給 AI 代理進行處理。

2.  **`sqlcheckmcpserver.py` (MCP 後端)**:
    -   作為一個 MCP 伺服器，提供一組可供 AI 代理使用的工具。
    -   負責與 Oracle 資料庫進行實際的連線與操作。
    -   將資料庫操作的結果回傳給 AI 代理。

## 🚀 開始使用

### 前置需求

-   Docker
-   Python 3.13+
-   `uv` (Python 套件安裝工具)
-   一個可連線的 Oracle 資料庫
-   一個可連線的 Ollama 服務

### 1. 複製專案

```bash
git clone <your-repository-url>
cd sql-mcp-client
```

### 2. 設定環境變數

在專案根目錄下建立一個 `.env` 檔案。您需要填寫以下變數：

```dotenv
# .env

# --- MCP/FastAPI Server ---
MCP_BASE_URL=http://localhost:8000

# --- Ollama LLM ---
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3:32b
OLLAMA_TEMPERATURE=0.5
OLLAMA_MAX_TOKENS=1000

# --- Oracle Database ---
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_DSN=your_db_host:1521/your_service_name

# --- MCP Server Path (for Docker) ---
SQL_MCP_SERVER_PATH=/app/sqlcheckmcpserver.py
```

**注意**:
-   在 Docker 環境中，`OLLAMA_BASE_URL` 中的 `host.docker.internal` 可以讓容器存取到主機上執行的 Ollama 服務。
-   請將 `DB_USER`, `DB_PASSWORD`, `DB_DSN` 替換成您自己的 Oracle 資料庫連線資訊。

### 3. 安裝依賴套件 (本機開發)

如果您想在本機執行，請使用 `uv` 安裝依賴套件：

```bash
uv pip sync
```

### 4. 使用 Docker 執行 (建議)

這是最簡單的啟動方式，可以確保環境一致性。

**a. 建置 Docker 映像檔:**

```bash
docker build -t sql-mcp-client .
```

**b. 執行 Docker 容器:**

這個指令會啟動容器，並將您在主機上的 `.env` 檔案掛載到容器中。

```bash
docker run -d -p 8000:8000 -v "$(pwd)/.env:/app/.env" sql-mcp-client
```

## ⚙️ API 使用方式

應用程式啟動後，您可以透過向 `/api/ai/query` 端點傳送 `POST` 請求來進行查詢。

### cURL 範例

**查詢資料表 DDL:**

```bash
curl -X POST http://localhost:8000/api/ai/query \
-H "Content-Type: application/json" \
-d '{"query": "幫我取得 EMPLOYEES 資料表的 DDL"}'
```

**執行 SELECT 查詢:**

```bash
curl -X POST http://localhost:8000/api/ai/query \
-H "Content-Type: application/json" \
-d '{"query": "從 EMPLOYEES 資料表中查詢前 5 筆員工資料"}'
```

## 📄 主要檔案

-   `api_optimized_api.py`: FastAPI 應用程式進入點。
-   `sqlcheckmcpserver.py`: MCP 伺服器，提供資料庫工具。
-   `Dockerfile`: 用於建置 Docker 映像檔。
-   `.env`: 環境變數設定檔 (需自行建立)。
-   `pyproject.toml`: 專案依賴套件定義。


## 📄 Docker 映像檔建置
1. 建置 Docker 映像檔：
```
docker build -t your-image-name . #(請將 your-image-name 替換成您想要的映像檔名稱)
```
2. 執行 Docker 容器並掛載 `.env` 檔案：
```
docker run -d -p 8000:8000 -v $(pwd)/.env:/app/.env your-image-name #(這裡的 $(pwd)/.env 會自動取得目前路徑下的 .env 檔案的絕對路徑)
```
