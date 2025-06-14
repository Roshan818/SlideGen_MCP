from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import httpx
import json
import os
from bs4 import BeautifulSoup

load_dotenv()

mcp = FastMCP("docs")

USER_AGENT = "docs-app/1.0"
SERPER_URL = "https://google.serper.dev/search"

docs_url = {
    "python": "docs.python.org/3/",
    "langchain": "python.langchain.com/docs/",
    "modelcontextprotocol": "modelcontextprotocol.io/introduction",
    "llama-index": "docs.llamaindex.ai/en/stable",
    "openai": "platform.openai.com/docs",
}


async def search_web(query: str) -> dict | None:
    api_key = os.getenv("SERPER_API_KEY")

    # Better error handling for missing API key
    if not api_key:
        raise ValueError(
            "SERPER_API_KEY not found in environment variables. Please check your .env file."
        )

    payload = json.dumps({"q": query, "num": 2})

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                SERPER_URL, headers=headers, data=payload, timeout=30.0
            )

            # More detailed error information
            if response.status_code == 403:
                raise httpx.HTTPStatusError(
                    f"403 Forbidden - API key may be invalid or expired. Status: {response.status_code}, Response: {response.text}",
                    request=response.request,
                    response=response,
                )

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            return {"organic": []}
        except httpx.HTTPStatusError as e:
            # Return more helpful error message
            return {"error": f"HTTP Error: {e}", "organic": []}


async def fetch_url(url: str):
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text()
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            return text
        except httpx.TimeoutException:
            return "Timeout Error: Could not fetch URL within 30 seconds"
        except httpx.HTTPStatusError as e:
            return f"HTTP Error fetching {url}: {e.response.status_code}"
        except Exception as e:
            return f"Error fetching {url}: {str(e)}"


@mcp.tool()
async def get_docs(query: str, library: str):
    """
    Search the docs for a given query and library.
    Supported libraries: python, langchain, modelcontextprotocol, llama-index, openai

    Args:
        query: The query to search for (e.g. "How to use Langchain")
        library: The library to search for (e.g. "langchain")

    Returns:
        String containing extracted text from relevant documentation pages.
    """
    if library not in docs_url:
        available_libs = ", ".join(docs_url.keys())
        raise ValueError(
            f"Invalid library: '{library}'. Supported libraries: {available_libs}"
        )

    search_query = f"site:{docs_url[library]} {query}"
    results = await search_web(search_query)

    # Handle search errors
    if "error" in results:
        return f"Search failed: {results['error']}"

    if not results.get("organic") or len(results["organic"]) == 0:
        return f"No results found for '{query}' in {library} documentation"

    text = f"Documentation search results for '{query}' in {library}:\n\n"

    for i, result in enumerate(results["organic"], 1):
        url = result["link"]
        title = result.get("title", "No title")

        text += f"=== Result {i}: {title} ===\n"
        text += f"URL: {url}\n\n"

        page_content = await fetch_url(url)

        # Limit content length to avoid overwhelming responses
        if len(page_content) > 5000:
            page_content = (
                page_content[:5000]
                + "\n\n[Content truncated - showing first 5000 characters]"
            )

        text += page_content
        text += "\n\n" + "=" * 50 + "\n\n"

    return text


@mcp.tool()
async def add_two_numbers_test(a: int, b: int):
    """
    Add two numbers together - test tool to verify MCP is working.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of the two numbers
    """
    return a + b


if __name__ == "__main__":
    print("MCP Server starting...")
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        print(f"Server error: {e}")
        raise
