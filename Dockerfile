# 使用官方 Python 3.13 slim 作為基礎映像
FROM python:3.13-slim

# 將工作目錄設定為 /app
WORKDIR /app

# 安裝 uv
RUN pip install uv

# 複製依賴定義檔案
COPY pyproject.toml uv.lock ./

# 使用 uv 安裝依賴
# 這會讀取 pyproject.toml 並安裝鎖定版本的依賴
RUN uv pip install . --system
# 複製所有專案檔案到工作目錄
COPY . .

# 開放 port 8000，讓容器外的服務可以存取
EXPOSE 8000

# 設定容器啟動時執行的指令
# 使用 uvicorn 來執行 FastMCP (FastAPI) 應用程式
# --host 0.0.0.0 讓服務可以從容器外部存取
CMD ["python", "api_optimized_api.py"]
