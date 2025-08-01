from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import oracledb
import json
from typing import Dict, Any
import os
from dotenv import load_dotenv


# Initialize FastMCP server
mcp = FastMCP("sql-check", log_level="INFO")


# Database connection configuration

# 載入 .env 檔案中的環境變數
load_dotenv(".env")

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "dsn": os.getenv("DB_DSN")
}
def get_db_connection():
    """Create and return Oracle database connection."""
    return oracledb.connect(**DB_CONFIG)

@mcp.tool()
def get_table_ddl(table_name: str) -> str:
    """Retrieve the DDL statement for a given Oracle table name."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Use DBMS_METADATA to get DDL
            cursor.execute("""
                SELECT DBMS_METADATA.GET_DDL('TABLE', :table_name, 'DBUSERNEB')
                FROM DUAL
            """, table_name=table_name.upper())
            
            result = cursor.fetchone()
            if result:
                return str(result[0])
            return f"No DDL found for table {table_name}"
    except oracledb.Error as e:
        return f"Error retrieving DDL: {str(e)}"

@mcp.tool()
def execute_select_query(params: Dict[str, Any]) -> str:
    """Execute a SELECT query on a given Oracle table and return results.
    Parameters: table_name (str) and query (str)."""
    table_name = params.get('table_name')
    query = params.get('query')
    
    if not table_name or not query:
        return "Error: Both table_name and query parameters are required"
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Validate that the query is a SELECT statement
            if not query.strip().upper().startswith('SELECT'):
                return "Error: Only SELECT queries are allowed"
                
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = cursor.fetchall()
            
            # Format results as JSON for better readability
            formatted_results = []
            for row in results:
                formatted_results.append(dict(zip(columns, row)))
                
            return json.dumps(formatted_results, default=str, indent=2)
    except oracledb.Error as e:
        return f"Error executing query: {str(e)}"



if __name__ == "__main__":
    print("start")  # 替换为实际表名
    # Initialize and run the server
    mcp.run(transport='stdio')