#!/usr/bin/env python3
"""
Test script for development - run this to test functions independently
Usage: uv run test_server.py
"""

# from mcp.server.fastmcp import FastMCP
# from dotenv import load_dotenv
import asyncio
import sys
import os
from main import get_docs, add_two_numbers_test


async def test_basic_functionality():
    """Test basic functionality without MCP protocol."""
    print("Testing MCP Server Functions")
    print("=" * 40)

    # Test the simple function first
    print("1. Testing add_two_numbers_test:")
    try:
        result = await add_two_numbers_test(5, 3)
        print(f"   5 + 3 = {result}")
        print("   ✅ Basic function test passed")
    except Exception as e:
        print(f"   ❌ Basic function test failed: {e}")
        return False

    print()

    # Test documentation search
    print("2. Testing get_docs function:")
    try:
        # Test with a simple query
        result = await get_docs("async", "python")
        print("   Query: async in python docs")
        print(f"   Result length: {len(result)} characters")

        if "No results found" in result:
            print("   ⚠️  No results found - this might be normal")
        elif "Error" in result:
            print(f"   ❌ Error in search: {result[:200]}...")
        else:
            print("   ✅ Documentation search test passed")
            # Show first 200 chars of result
            print(f"   Preview: {result[:200]}...")

    except Exception as e:
        print(f"   ❌ Documentation search test failed: {e}")
        return False

    print()
    print("All tests completed!")
    return True


async def test_all_libraries():
    """Test all supported libraries."""
    libraries = ["python", "langchain", "modelcontextprotocol", "llama-index", "openai"]

    print("Testing all supported libraries:")
    print("=" * 40)

    for lib in libraries:
        print(f"Testing {lib}...")
        try:
            result = await get_docs("tutorial", lib)
            if len(result) > 100:
                print(f"   ✅ {lib}: Success ({len(result)} chars)")
            else:
                print(f"   ⚠️  {lib}: Short result ({len(result)} chars)")
        except Exception as e:
            print(f"   ❌ {lib}: Failed - {e}")


def main():
    """Main test function."""
    print("MCP Server Development Test")
    print("=" * 50)

    # Check environment
    if not os.getenv("SERPER_API_KEY"):
        print("⚠️  Warning: SERPER_API_KEY not found in environment")
        print("   Documentation search may fail")
        print()

    try:
        # Run basic tests
        success = asyncio.run(test_basic_functionality())

        if success:
            print("\n" + "=" * 50)
            response = input("Run extended library tests? (y/n): ")
            if response.lower() == "y":
                asyncio.run(test_all_libraries())

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
