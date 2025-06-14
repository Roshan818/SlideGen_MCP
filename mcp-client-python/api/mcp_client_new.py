from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
import logging
import os
import sys
import asyncio

# import subprocess
import json
# from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    from pydantic_settings import BaseSettings
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

load_dotenv()


class Settings(BaseSettings):
    server_script_path: str = "D:\\2025\\pyth\\documentation\\main.py"
    python_executable: str = sys.executable  # Use current Python executable
    debug_mode: bool = True

    class Config:
        env_file = ".env"


settings = Settings()


class MCPStdioClient:
    """MCP Client that communicates with stdio-based MCP servers"""

    def __init__(self):
        self.process = None
        self.connected = False
        self.request_id = 0

    async def connect_to_server(self, script_path: str) -> bool:
        """Connect to MCP server using stdio transport"""
        try:
            logger.info(f"Starting MCP server process: {script_path}")

            # Start the MCP server as a subprocess
            self.process = await asyncio.create_subprocess_exec(
                settings.python_executable,
                script_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(script_path),
            )

            # Initialize MCP connection
            init_request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "fastapi-mcp-client", "version": "1.0.0"},
                },
            }

            # Send initialize request
            response = await self._send_request(init_request)
            if response and "result" in response:
                logger.info("MCP server initialized successfully")

                # Send initialized notification
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                }
                await self._send_notification(initialized_notification)

                self.connected = True
                return True
            else:
                logger.error(f"Failed to initialize MCP server: {response}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            if self.process:
                await self._cleanup_process()
            return False

    def _next_id(self) -> int:
        """Generate next request ID"""
        self.request_id += 1
        return self.request_id

    async def _send_request(self, request: dict) -> dict:
        """Send a JSON-RPC request and wait for response"""
        if not self.process:
            raise RuntimeError("Not connected to server")

        try:
            # Send request
            request_line = json.dumps(request) + "\n"
            self.process.stdin.write(request_line.encode())
            await self.process.stdin.drain()

            # Read response
            response_line = await self.process.stdout.readline()
            if not response_line:
                raise RuntimeError("Server closed connection")

            response = json.loads(response_line.decode().strip())
            return response

        except Exception as e:
            logger.error(f"Error sending request: {e}")
            raise

    async def _send_notification(self, notification: dict):
        """Send a JSON-RPC notification (no response expected)"""
        if not self.process:
            raise RuntimeError("Not connected to server")

        try:
            notification_line = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_line.encode())
            await self.process.stdin.drain()
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            raise

    async def get_mcp_tools(self) -> List[dict]:
        """Get available tools from MCP server"""
        request = {"jsonrpc": "2.0", "id": self._next_id(), "method": "tools/list"}

        response = await self._send_request(request)
        if "result" in response and "tools" in response["result"]:
            return response["result"]["tools"]
        else:
            logger.error(f"Failed to get tools: {response}")
            return []

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a specific tool"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }

        response = await self._send_request(request)
        if "result" in response:
            return response["result"]
        else:
            logger.error(f"Tool call failed: {response}")
            raise RuntimeError(
                f"Tool call failed: {response.get('error', 'Unknown error')}"
            )

    async def process_query(self, query: str) -> List[dict]:
        """Process a query using available tools"""
        # This is a simplified implementation
        # In a real implementation, you'd have logic to determine which tools to use
        messages = []

        try:
            # For now, let's just return the query as a message
            # You can enhance this to actually process the query with tools
            messages.append(
                {
                    "role": "assistant",
                    "content": f"Received query: {query}. Available tools can be called via /tool endpoint.",
                }
            )

            return messages

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return [{"role": "error", "content": str(e)}]

    async def _cleanup_process(self):
        """Clean up the subprocess"""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Process didn't terminate gracefully, killing it")
                self.process.kill()
                await self.process.wait()
            except Exception as e:
                logger.error(f"Error during process cleanup: {e}")

    async def cleanup(self):
        """Clean up resources"""
        self.connected = False
        await self._cleanup_process()
        logger.info("MCP client cleanup completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with improved error handling"""
    client = None

    try:
        logger.info("Starting MCP client connection...")

        # Check if server script exists
        if not os.path.exists(settings.server_script_path):
            raise FileNotFoundError(
                f"MCP server script not found: {settings.server_script_path}"
            )

        logger.info(f"Found MCP server script at: {settings.server_script_path}")

        # Initialize client
        client = MCPStdioClient()
        logger.info("MCP client initialized")

        # Attempt connection
        logger.info("Attempting to connect to MCP server...")
        connected = await client.connect_to_server(settings.server_script_path)

        if not connected:
            raise ConnectionError("MCP client returned False for connection attempt")

        logger.info("Successfully connected to MCP server")

        # Test the connection by getting available tools
        try:
            tools = await client.get_mcp_tools()
            logger.info(f"MCP server has {len(tools)} tools available")
            for tool in tools:
                logger.info(
                    f"  - {tool.get('name', 'unnamed')}: {tool.get('description', 'no description')}"
                )
        except Exception as e:
            logger.warning(
                f"Could not retrieve tools (connection may be unstable): {e}"
            )

        # Store client in app state
        app.state.client = client
        app.state.connected = True

        logger.info("MCP client startup completed successfully")
        yield

    except Exception as e:
        logger.error(f"Failed to connect to MCP server: {e}")
        logger.error(f"Error type: {type(e).__name__}")

        if settings.debug_mode:
            import traceback

            logger.error(f"Full traceback:\n{traceback.format_exc()}")

        app.state.client = client  # Store even failed client for cleanup
        app.state.connected = False
        app.state.startup_error = str(e)
        yield  # Allow app to start but mark as disconnected

    finally:
        # Cleanup
        if client:
            try:
                logger.info("Cleaning up MCP client...")
                await client.cleanup()
                logger.info("MCP client cleanup completed")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")


app = FastAPI(
    title="MCP Chatbot API",
    description="API for interacting with MCP (Model Context Protocol) servers via stdio",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class QueryRequest(BaseModel):
    query: str


class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    mcp_connected: bool
    error: Optional[str] = None
    server_script_path: str


def check_mcp_connection():
    """Helper function to check if MCP is connected"""
    if not hasattr(app.state, "connected") or not app.state.connected:
        error_msg = getattr(app.state, "startup_error", "MCP server not connected")
        raise HTTPException(
            status_code=503, detail=f"MCP server not available: {error_msg}"
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    connected = hasattr(app.state, "connected") and app.state.connected
    error = getattr(app.state, "startup_error", None) if not connected else None

    return HealthResponse(
        status="healthy" if connected else "unhealthy",
        mcp_connected=connected,
        error=error,
        server_script_path=settings.server_script_path,
    )


@app.get("/tools")
async def get_available_tools():
    """Get list of available tools"""
    check_mcp_connection()

    try:
        tools = await app.state.client.get_mcp_tools()
        return {
            "tools": [
                {
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "input_schema": tool.get("inputSchema", {}),
                }
                for tool in tools
            ]
        }
    except Exception as e:
        logger.error(f"Error getting tools: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tools: {str(e)}")


@app.post("/query")
async def process_query(request: QueryRequest):
    """Process a query and return the response"""
    check_mcp_connection()

    try:
        logger.info(f"Processing query: {request.query[:100]}...")
        messages = await app.state.client.process_query(request.query)
        logger.info(f"Query processed successfully, returned {len(messages)} messages")
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process query: {str(e)}"
        )


@app.post("/tool")
async def call_tool(tool_call: ToolCall):
    """Call a specific tool"""
    check_mcp_connection()

    try:
        logger.info(f"Calling tool: {tool_call.name} with args: {tool_call.args}")
        result = await app.state.client.call_tool(tool_call.name, tool_call.args)
        logger.info("Tool call completed successfully")
        return {"result": result}
    except Exception as e:
        logger.error(f"Error calling tool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to call tool: {str(e)}")


@app.get("/debug/info")
async def debug_info():
    """Debug information endpoint"""
    if not settings.debug_mode:
        raise HTTPException(status_code=404, detail="Debug mode disabled")

    return {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "working_directory": os.getcwd(),
        "server_script_path": settings.server_script_path,
        "server_script_exists": os.path.exists(settings.server_script_path),
        "mcp_connected": hasattr(app.state, "connected") and app.state.connected,
        "startup_error": getattr(app.state, "startup_error", None),
        "settings": settings.dict(),
    }


if __name__ == "__main__":
    import uvicorn

    # Check dependencies
    required_packages = ["python-dotenv"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        logger.error(f"Missing required packages: {missing_packages}")
        logger.error(
            "Please install them with: pip install " + " ".join(missing_packages)
        )
        sys.exit(1)

    # Run with better error handling
    try:
        logger.info("Starting FastAPI server...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info" if settings.debug_mode else "warning",
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)
