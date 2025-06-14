# Debug script to test MCP server connection
import asyncio
import sys
import os
# from pathlib import Path


async def test_server_connection():
    """Test if the MCP server can be started and connected to"""

    # 1. Check if the server script exists
    server_path = "D:\\2025\\pyth\\documentation\\main.py"
    print(f"1. Checking if server script exists: {server_path}")

    if not os.path.exists(server_path):
        print("❌ Server script not found!")
        return False
    else:
        print("✅ Server script found")

    # 2. Check if the script is executable Python
    print("2. Checking if script is valid Python...")
    try:
        with open(server_path, "r") as f:
            content = f.read()
            # Basic check for Python syntax
            compile(content, server_path, "exec")
        print("✅ Script appears to be valid Python")
    except Exception as e:
        print(f"❌ Script has syntax errors: {e}")
        return False

    # 3. Try to import and test the MCP client
    print("3. Testing MCP client import...")
    try:
        from mcp_client import MCPClient

        print("✅ MCPClient imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import MCPClient: {e}")
        return False

    # 4. Try to create and connect the client
    print("4. Testing MCP client connection...")
    client = MCPClient()

    try:
        print("   - Attempting to connect to server...")
        connected = await client.connect_to_server(server_path)

        if connected:
            print("✅ Successfully connected to MCP server!")

            # Test getting tools
            try:
                tools = await client.get_mcp_tools()
                print(f"✅ Found {len(tools)} tools available")
                for tool in tools:
                    print(f"   - {tool.name}: {tool.description}")
            except Exception as e:
                print(f"⚠️  Connected but failed to get tools: {e}")

            return True
        else:
            print("❌ Failed to connect to server (returned False)")
            return False

    except Exception as e:
        print(f"❌ Connection failed with error: {e}")
        return False

    finally:
        try:
            await client.cleanup()
            print("✅ Client cleanup completed")
        except:
            pass


# Additional debugging functions
def check_environment():
    """Check the Python environment and dependencies"""
    print("=== Environment Check ===")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")

    # Check for required packages
    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic_settings",
        "python-dotenv",
    ]
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")


def check_mcp_server_script():
    """Examine the MCP server script for common issues"""
    server_path = "D:\\2025\\pyth\\documentation\\main.py"
    print("\n=== MCP Server Script Analysis ===")

    if not os.path.exists(server_path):
        print(f"❌ Server script not found at: {server_path}")
        return

    try:
        with open(server_path, "r") as f:
            content = f.read()

        print(f"✅ Script exists and is readable ({len(content)} characters)")

        # Check for common MCP server patterns
        if "mcp" in content.lower():
            print("✅ Script appears to be MCP-related")
        else:
            print("⚠️  Script may not be an MCP server (no 'mcp' found)")

        if "server" in content.lower():
            print("✅ Script appears to be a server")

        if "__main__" in content:
            print("✅ Script has main execution block")
        else:
            print("⚠️  Script may not be directly executable (no __main__ block)")

    except Exception as e:
        print(f"❌ Error reading server script: {e}")


async def main():
    """Main debugging function"""
    print("=== MCP Connection Debugger ===\n")

    # Step 1: Check environment
    check_environment()

    # Step 2: Check MCP server script
    check_mcp_server_script()

    # Step 3: Test connection
    print("\n=== Connection Test ===")
    success = await test_server_connection()

    if success:
        print("\n🎉 All tests passed! Your MCP setup should work.")
    else:
        print("\n❌ Some tests failed. Check the issues above.")
        print("\n💡 Common solutions:")
        print("   - Make sure the MCP server script is correct and executable")
        print("   - Check that all required dependencies are installed")
        print("   - Verify the server path is correct")
        print("   - Make sure the MCP server is designed to be started this way")


if __name__ == "__main__":
    asyncio.run(main())
