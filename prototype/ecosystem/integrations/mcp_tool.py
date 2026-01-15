"""
MCP Tool - AIO Parser as an MCP (Model Context Protocol) Tool.

This module provides the AIO parser as a tool that AI agents can invoke
through the MCP standard. Compatible with Claude Desktop, Cursor, and
other MCP-enabled applications.

Tool Definition:
    name: aio_web_fetch
    description: Fetch web content using AIO-aware parser for cleaner results
    parameters:
        url: string (required) - URL to fetch
        query: string (optional) - Query for targeted chunk retrieval
"""

import json
from typing import Optional
from dataclasses import dataclass


@dataclass
class MCPToolResult:
    """Result from MCP tool invocation."""
    success: bool
    content: str
    metadata: dict
    error: Optional[str] = None
    
    def to_mcp_response(self) -> dict:
        """Format as MCP tool response."""
        if self.success:
            return {
                "type": "text",
                "text": self.content,
                "metadata": self.metadata
            }
        else:
            return {
                "type": "error",
                "error": self.error or "Unknown error"
            }


def aio_web_fetch(url: str, query: Optional[str] = None) -> MCPToolResult:
    """
    MCP Tool: Fetch web content using AIO-aware parser.
    
    This tool:
    1. Checks if the target URL has AIO content available
    2. If yes: returns clean, indexed content from .aio file
    3. If no: falls back to HTML scraping with noise removal
    
    Args:
        url: The URL to fetch content from
        query: Optional query for targeted chunk retrieval
        
    Returns:
        MCPToolResult with clean content and metadata
    """
    try:
        from aio_parser import parse
        
        envelope = parse(url, query=query)
        
        # Format metadata for AI
        metadata = {
            "source_url": envelope.source_url,
            "source_type": envelope.source_type,
            "tokens": envelope.tokens,
            "noise_score": envelope.noise_score,
            "aio_detected": envelope.source_type == "aio",
            "chunks_available": len(envelope.chunks),
        }
        
        # Add chunk summaries if available
        if envelope.chunks:
            metadata["chunk_index"] = [
                {"id": c.id, "title": c.title, "summary": c.summary}
                for c in envelope.chunks
            ]
        
        return MCPToolResult(
            success=True,
            content=envelope.narrative,
            metadata=metadata
        )
        
    except Exception as e:
        return MCPToolResult(
            success=False,
            content="",
            metadata={"url": url},
            error=str(e)
        )


# MCP Tool Definition (JSON Schema)
MCP_TOOL_DEFINITION = {
    "name": "aio_web_fetch",
    "description": """Fetch web content using AIO-aware parser for cleaner results.

This tool implements the AIO (AI Optimization) protocol to retrieve web content 
in a machine-optimized format. When a website supports AIO, this tool retrieves 
clean, indexed content directly. For non-AIO sites, it falls back to HTML 
scraping with noise removal.

Benefits over standard web fetching:
- 68-83% token reduction
- Near-zero noise score for AIO sites
- Indexed chunks for targeted retrieval
- Better accuracy due to cleaner input

Use this tool when you need to fetch web content for analysis, summarization,
or answering questions about a webpage.""",
    
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch content from"
            },
            "query": {
                "type": "string",
                "description": "Optional query for targeted chunk retrieval. If provided, only chunks matching the query keywords will be returned."
            }
        },
        "required": ["url"]
    }
}


class AIOWebFetchTool:
    """
    MCP Tool class for AI agent frameworks.
    
    Usage with various frameworks:
    
    1. Claude Desktop / Cursor:
       Add to MCP config and this tool will be available
       
    2. LangChain:
       from langchain.tools import Tool
       tool = Tool.from_function(
           func=aio_tool.invoke,
           name=aio_tool.name,
           description=aio_tool.description
       )
       
    3. OpenAI Function Calling:
       Use get_openai_function() to get the function definition
    """
    
    name = "aio_web_fetch"
    description = MCP_TOOL_DEFINITION["description"]
    
    def invoke(self, url: str, query: Optional[str] = None) -> str:
        """Invoke the tool and return content string."""
        result = aio_web_fetch(url, query)
        if result.success:
            return result.content
        else:
            return f"Error: {result.error}"
    
    def get_mcp_definition(self) -> dict:
        """Get MCP tool definition."""
        return MCP_TOOL_DEFINITION
    
    def get_openai_function(self) -> dict:
        """Get OpenAI function calling definition."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": MCP_TOOL_DEFINITION["inputSchema"]
        }
    
    def get_anthropic_tool(self) -> dict:
        """Get Anthropic Claude tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": MCP_TOOL_DEFINITION["inputSchema"]
        }


# Singleton instance for easy import
aio_tool = AIOWebFetchTool()


# MCP Server implementation (for direct MCP hosting)
def handle_mcp_request(request: dict) -> dict:
    """
    Handle an MCP request.
    
    This function can be used to implement a simple MCP server.
    """
    method = request.get("method")
    
    if method == "tools/list":
        return {
            "tools": [MCP_TOOL_DEFINITION]
        }
    
    elif method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "aio_web_fetch":
            result = aio_web_fetch(
                url=arguments.get("url"),
                query=arguments.get("query")
            )
            return result.to_mcp_response()
        else:
            return {"type": "error", "error": f"Unknown tool: {tool_name}"}
    
    else:
        return {"type": "error", "error": f"Unknown method: {method}"}


if __name__ == "__main__":
    # Demo usage
    print("AIO Web Fetch MCP Tool")
    print("=" * 40)
    print("\nTool Definition:")
    print(json.dumps(MCP_TOOL_DEFINITION, indent=2))
    
    print("\n\nExample usage:")
    print('  result = aio_web_fetch("https://example.com", query="pricing")')
    print('  print(result.content)')
