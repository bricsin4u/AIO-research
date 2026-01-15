"""
n8n Integration - AIO Parser for n8n Execute Code Node.

This module provides ready-to-use code snippets for n8n workflows.
It can be used in the "Execute Code" node to fetch web content
using the AIO-aware parser.

Usage in n8n:
1. Add an "Execute Code" node 
2. Set language to Python
3. Copy the code from aio_n8n_fetch() function
4. Configure input/output items

Alternatively, if aio_parser is installed in n8n's Python environment,
you can import it directly.
"""

import json
from typing import Dict, List, Any


def aio_n8n_fetch(input_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    n8n Execute Code function for AIO-aware web fetching.
    
    Expected input item structure:
    {
        "json": {
            "url": "https://example.com",
            "query": "optional search query"
        }
    }
    
    Output structure:
    {
        "json": {
            "url": "...",
            "source_type": "aio" | "scraped",
            "content": "clean markdown content",
            "tokens": 123,
            "noise_score": 0.0,
            "relevance_ratio": 1.0,
            "aio_detected": true
        }
    }
    """
    from aio_parser import parse
    
    output_items = []
    
    for item in input_items:
        data = item.get("json", {})
        url = data.get("url")
        query = data.get("query", None)
        
        if not url:
            output_items.append({
                "json": {
                    "error": "No URL provided",
                    "success": False
                }
            })
            continue
        
        try:
            envelope = parse(url, query=query)
            
            output_items.append({
                "json": {
                    "url": url,
                    "source_type": envelope.source_type,
                    "content": envelope.narrative,
                    "tokens": envelope.tokens,
                    "noise_score": envelope.noise_score,
                    "relevance_ratio": envelope.relevance_ratio,
                    "aio_detected": envelope.source_type == "aio",
                    "success": True
                }
            })
        except Exception as e:
            output_items.append({
                "json": {
                    "url": url,
                    "error": str(e),
                    "success": False
                }
            })
    
    return output_items


# Standalone code for n8n Execute Code node (copy this directly)
N8N_CODE_SNIPPET = '''
# AIO-Aware Web Fetcher for n8n
# Copy this code into an Execute Code node (Python)

import requests
from bs4 import BeautifulSoup
import json
import re

def discover_aio(url):
    """Check for AIO availability."""
    try:
        from urllib.parse import urljoin, urlparse
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check robots.txt for AIO directive
        robots_url = urljoin(base_url, "/robots.txt")
        response = requests.get(robots_url, timeout=5)
        if response.status_code == 200:
            for line in response.text.split("\\n"):
                if line.lower().startswith("aio-content:"):
                    return urljoin(base_url, line.split(":", 1)[1].strip())
        
        # Try direct URL
        aio_url = urljoin(base_url, "/ai-content.aio")
        response = requests.head(aio_url, timeout=5)
        if response.status_code == 200:
            return aio_url
            
    except:
        pass
    return None

def parse_aio(url, query=None):
    """Parse URL with AIO detection."""
    aio_url = discover_aio(url)
    
    if aio_url:
        # Fetch AIO content
        response = requests.get(aio_url, timeout=10)
        data = response.json()
        
        # Combine all content
        content = "\\n\\n".join(
            c.get("content", "") 
            for c in data.get("content", [])
        )
        
        return {
            "source_type": "aio",
            "content": content,
            "tokens": len(content) // 4,
            "noise_score": 0.0,
            "aio_detected": True
        }
    else:
        # Fallback to scraping
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove noise
        for tag in soup.find_all(["nav", "footer", "script", "style"]):
            tag.decompose()
        
        text = soup.get_text(separator="\\n", strip=True)
        
        return {
            "source_type": "scraped",
            "content": text,
            "tokens": len(text) // 4,
            "noise_score": 0.7,
            "aio_detected": False
        }

# Main execution
output_items = []
for item in $input.all():
    url = item.json.get("url")
    if url:
        result = parse_aio(url)
        result["url"] = url
        result["success"] = True
        output_items.append({"json": result})
    else:
        output_items.append({"json": {"error": "No URL", "success": False}})

return output_items
'''


def get_n8n_workflow_template() -> dict:
    """
    Returns a complete n8n workflow template with AIO fetching.
    Import this JSON into n8n to get started.
    """
    return {
        "name": "AIO Web Fetcher",
        "nodes": [
            {
                "parameters": {},
                "id": "trigger",
                "name": "Manual Trigger",
                "type": "n8n-nodes-base.manualTrigger",
                "position": [250, 300]
            },
            {
                "parameters": {
                    "values": {
                        "string": [
                            {
                                "name": "url",
                                "value": "https://example.com"
                            }
                        ]
                    }
                },
                "id": "set-url",
                "name": "Set URL",
                "type": "n8n-nodes-base.set",
                "position": [450, 300]
            },
            {
                "parameters": {
                    "mode": "runOnceForAllItems",
                    "language": "python",
                    "pythonCode": N8N_CODE_SNIPPET
                },
                "id": "aio-fetch",
                "name": "AIO Fetch",
                "type": "n8n-nodes-base.code",
                "position": [650, 300]
            }
        ],
        "connections": {
            "Manual Trigger": {
                "main": [[{"node": "Set URL", "type": "main", "index": 0}]]
            },
            "Set URL": {
                "main": [[{"node": "AIO Fetch", "type": "main", "index": 0}]]
            }
        }
    }


if __name__ == "__main__":
    # Print the code snippet for manual copy
    print("=" * 60)
    print("n8n Execute Code Snippet")
    print("=" * 60)
    print(N8N_CODE_SNIPPET)
