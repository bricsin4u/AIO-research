# AIO MCP Server Integration

**Type**: Model Context Protocol (MCP) Server  
**Path**: `integrations/mcp_tool.py`  
**Compatibility**: Claude Desktop, Cursor, LangChain

The **AIO MCP Server** exposes the AIO parser as a tool to your AI agents. This allows LLMs (like Claude) to browse the web using the token-efficient AIO protocol instead of standard HTML scraping.

---

## Features

- **Token Efficiency**: Consumes 90% fewer tokens than raw HTML.
- **Noise Reduction**: AI gets only the relevant content, improving reasoning.
- **Targeted Retrieval**: AI can request specific chunks (e.g., "pricing") to save context.

---

## Installation (Claude Desktop)

To give Claude Desktop access to AIO browsing:

1.  **Prerequisites**: Ensure Python 3.8+ is installed.
2.  **Locate Config**: Open `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac).
3.  **Add Server**:
    ```json
    {
      "mcpServers": {
        "aio-browser": {
          "command": "python",
          "args": [
            "C:/Path/To/AIOv2/integrations/mcp_server.py"
          ]
        }
      }
    }
    ```
    *(Note: You'll need to create the wrapper script `mcp_server.py` described below)*

---

## Usage

Once connected, you can ask Claude:

> "Browse https://example.com/docs and tell me about the API authentication."

Claude will:
1.  Call `aio_web_fetch(url="https://example.com/docs", query="authentication")`.
2.  Receive clean, summarized Markdown.
3.  Answer your question accurately without hallucinating from sidebar noise.

---

## Integration Code

The core tool definition resides in `integrations/mcp_tool.py`.

### LangChain Integration

```python
from integrations.mcp_tool import aio_tool
from langchain.agents import initialize_agent, AgentType

tools = [
    Tool(
        name=aio_tool.name,
        func=aio_tool.invoke,
        description=aio_tool.description
    )
]

agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
agent.run("Browse http://example.com")
```

---

## Server Wrapper Script

To run this as a standalone MCP server (stdio), create `integrations/mcp_server.py`:

```python
import sys
import json
from mcp_tool import handle_mcp_request

def main():
    # Read MCP JSON-RPC requests from stdin
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_mcp_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
        except Exception as e:
            # Log error
            pass

if __name__ == "__main__":
    main()
```
