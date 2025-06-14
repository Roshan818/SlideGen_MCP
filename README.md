Here’s a polished and professional `README.md` for your MCP tool setup:

---

# Automated MCP SlideGen Tool

This project consists of three MCP (Model Context Protocol) servers integrated with the Claude Desktop app to power context-aware GenAI workflows. Each server specializes in a unique task:

* `documentation`: Scrapes and summarizes webpages.
* `ppt_generator`: Generates McKinsey-style PowerPoint slides from documents.
* `pdf_analyzer`: Extracts and processes information from PDFs.

The MCP servers are configured via Claude’s JSON setup and managed with [`uv`](https://github.com/astral-sh/uv) for fast, reproducible Python environments.

---

## Quickstart

### 1. Install `uv`

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

### 2. Install and Set Up MCP Servers

Clone or organize your project directory like this:

```
D:\2025\pyth\
├── documentation\
│   └── main.py
├── ppt_generator\
│   └── main.py
├── pdf_analyzer\
│   └── main.py
```

### 3. Install Dependencies Using `uv`

Run the following inside each respective folder:

#### `documentation`:

```bash
uv add bs4 httpx "mcp[cli]" python-dotenv
```

#### `ppt_generator`:

```bash
uv add fitz httpx "mcp[cli]" numpy pillow pymupdf python-dotenv python-pptx scikit-learn
```

#### `pdf_analyzer`:

```bash
uv add httpx "mcp[cli]" nltk numpy pymupdf pypdf2 scikit-learn
```

---

### 4. Configure Claude Desktop

Update your `claude.config.json` (or the relevant config file) to point to each MCP server:

```json
{
  "mcpServers": {
    "documentation": {
      "command": "C:\\Users\\Rosha\\.local\\bin\\uv.exe",
      "args": ["--directory", "D:\\2025\\pyth\\documentation", "run", "main.py"],
      "env": {}
    },
    "ppt_generator": {
      "command": "C:\\Users\\Rosha\\.local\\bin\\uv.exe",
      "args": ["--directory", "D:\\2025\\pyth\\ppt_generator", "run", "main.py"],
      "env": {}
    },
    "pdf_analyzer": {
      "command": "C:\\Users\\Rosha\\.local\\bin\\uv.exe",
      "args": ["--directory", "D:\\2025\\pyth\\pdf_analyzer", "run", "main.py"],
      "env": {}
    }
  }
}
```

---

### 5. Run the Servers

In each project directory:

```bash
uv run main.py
```

#### Development Mode (with Inspector)

```bash
npx @modelcontextprotocol/inspector uv run main.py
```

---

## MCP Client & Frontend (To Do)

* [ ] Implement MCP Client
* [ ] Create Streamlit UI Frontend

---

## Verification

Once configured and running, you should see your tools listed under the **Tools** section in the Claude Desktop app. Each tool will be callable from within Claude using its context-aware interface.

---

## Project Status

| Component       | Status      |
| --------------- | ----------- |
| `documentation` | ✅ Completed |
| `ppt_generator` | ✅ Completed |
| `pdf_analyzer`  | ✅ Completed |
| `mcp-client`    | ⏳ To Do     |
| Streamlit UI    | ⏳ To Do     |

---

## 🙌 Credits

Built with ❤️ by Roshan Kumar.
Powered by [Model Context Protocol](https://github.com/modelcontextprotocol).

