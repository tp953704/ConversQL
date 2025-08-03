import contextlib
import json
import logging
import os
from typing import Any, AsyncIterator, Dict, Optional, Union
import asyncio
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel
import uvicorn
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_mcp_client")


class MCPClientConfig(BaseModel):
    """Configuration for MCP Client"""
    base_url: str
    timeout: int = 30
    log_level: str = "INFO"


class MCPClient:
    """
    Enhanced MCP Client with LangChain and Ollama integration for AI-powered operations.
    """

    def __init__(
        self,
        base_url: str,
        config: Optional[MCPClientConfig] = None,
        log_level: Optional[str] = None,
        ollama_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the MCP client with AI capabilities.
        """
        self.config = config or MCPClientConfig(base_url=base_url)
        
        if log_level:
            logger.setLevel(getattr(logging, log_level))
        else:
            logger.setLevel(getattr(logging, self.config.log_level))

        # HTTP clients
        self._async_client = httpx.AsyncClient(
            base_url=self.config.base_url, 
            timeout=self.config.timeout
        )
        self._sync_client = httpx.Client(
            base_url=self.config.base_url, 
            timeout=self.config.timeout
        )

        # AI components
        self.llm = self._initialize_llm(ollama_config)
        self._mcp_available = True
        self._stdio_server_params = None
        
        logger.info(f"MCPClient initialized with base URL: {base_url}")

    def _initialize_llm(self, ollama_config: Optional[Dict[str, Any]]) -> Optional[ChatOllama]:
        """Initialize the Ollama language model"""
        if not ollama_config:
            return None
            
        return ChatOllama(
            base_url=ollama_config.get("base_url", "http://localhost:11434"),
            model=ollama_config.get("model", "llama2"),
            temperature=ollama_config.get("temperature", 0.5),
            max_tokens=ollama_config.get("max_tokens", 1000)
        )

    def configure_stdio_server(self, command: str, args: list):
        """Configure stdio server parameters for direct MCP communication."""
        self._stdio_server_params = StdioServerParameters(
            command=command,
            args=args,
        )

    async def _get_agent(self, session: ClientSession):
        """Create a LangChain agent with MCP tools."""
        tools = await load_mcp_tools(session)
        return create_react_agent(self.llm, tools)

    async def ai_query(self, query: str) -> str:
        """
        Execute a query using the AI agent with MCP tools.
        """
        if not self._stdio_server_params:
            raise MCPClientError("Stdio server not configured")
            
        async with stdio_client(self._stdio_server_params) as (read, write):    
            async with ClientSession(read_stream=read, write_stream=write) as session:
                await session.initialize()
                logger.info("Session initialized")
                
                agent = await self._get_agent(session)
                result = await agent.ainvoke({
                    "messages": [HumanMessage(content=query)]
                })
                
                return result["messages"][-1].content

    async def close(self) -> None:
        """Close all resources."""
        await self._async_client.aclose()
        self._sync_client.close()


# FastAPI Application Setup
app = FastAPI(title="MCP Client API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AIQueryRequest(BaseModel):
    query: str


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI"""
    logger.info("Starting up MCP Client API")
    yield
    logger.info("Shutting down MCP Client API")


app = FastAPI(title="MCP Client API", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/api/ai/query")
async def query_ai(request: AIQueryRequest):
    """
    Endpoint for AI queries using MCP tools
    """
    client = MCPClient(
        base_url=os.getenv("MCP_BASE_URL", "http://localhost:8000"),
        ollama_config={
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://192.168.8.111:11434"),
            "model": os.getenv("OLLAMA_MODEL", "qwen3:32b"),
            "temperature": float(os.getenv("OLLAMA_TEMPERATURE", 0.5)),
            "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", 1000))
        }
    )
    
    try:
        # The path inside the container will be /app/sqlcheckmcpserver.py
        sql_mcp_server_path = os.getenv("SQL_MCP_SERVER_PATH", "/app/sqlcheckmcpserver.py")
        client.configure_stdio_server(
            command="python",
            args=[sql_mcp_server_path],
        )
        response = await client.ai_query(request.query)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error processing AI query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()

@app.websocket("/ws/ai/query")
async def websocket_ai_query(websocket: WebSocket):
    await websocket.accept()
    client = None
    
    try:
        # Initialize client (same as HTTP version)
        client = MCPClient(
            base_url=os.getenv("MCP_BASE_URL", "http://localhost:8000"),
            ollama_config={
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://192.168.8.111:11434"),
                "model": os.getenv("OLLAMA_MODEL", "qwen3:32b"),
                "temperature": float(os.getenv("OLLAMA_TEMPERATURE", 0.5)),
                "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", 1000))
            }
        )
        
        # Configure stdio server
        sql_mcp_server_path = os.getenv("SQL_MCP_SERVER_PATH", "/app/sqlcheckmcpserver.py")
        client.configure_stdio_server(
            command="python",
            args=[sql_mcp_server_path],
        )

        while True:
            # Receive query from client
            query = await websocket.receive_text()
            
            # Process query and send back response
            response = await client.ai_query(query)
            cleaned_response = response.replace('<think>', '').replace('</think>', '').strip()
            await websocket.send_text(cleaned_response)
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.send_text(f"Error: {str(e)}")
    finally:
        if client:
            await client.close()

def run_server():
    """Run the FastAPI server"""
    config = uvicorn.Config(
        "api_optimized_api:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


if __name__ == "__main__":
    run_server()