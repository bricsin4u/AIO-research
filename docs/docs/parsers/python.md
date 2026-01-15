# Python AIO SDK Documentation

**Package**: `item_adapter`  
**Version**: `1.0.0`  
**License**: MIT

The Python SDK is the reference implementation of the AIO Consumer Protocol. It provides a robust, type-safe interface for integrating AIO content into LLM pipelines (LangChain, LlamaIndex) and Data Science workflows.

---

## Installation

```bash
pip install aio-parser
```

*Requirements: Python 3.8+*

---

## Quick Start

```python
from aio_parser import parse, AIOError

try:
    # Auto-resolves: AIO -> Fallback to Scrape
    envelope = parse("https://example.com/article")
    
    print(f"Source: {envelope.source_type}")  # 'aio' or 'scraped'
    print(f"Confidence: {envelope.noise_score}") # 0.0 (Perfect) to 1.0 (Noisy)
    
except AIOError as e:
    print(f"Fatal error: {e}")
```

---

## API Reference

### `parse()`

The main entry point for content retrieval.

```python
def parse(
    url: str, 
    query: str = None, 
    timeout: int = 10,
    user_agent: str = "AIO-Parser/1.0"
) -> ContentEnvelope
```

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `url` | `str` | Required | The target URL to process. |
| `query` | `str` | `None` | Optional keywords for **Targeted Retrieval**. |
| `timeout` | `int` | `10` | HTTP timeout in seconds. |

**Returns**: [`ContentEnvelope`](#contentenvelope)

---

### `ContentEnvelope`

The standardized data object returned by all AIO parsers.

```python
@dataclass
class ContentEnvelope:
    id: str           # Unique Request ID
    source_url: str   # The requested URL
    source_type: str  # "aio" (Verified) | "scraped" (Fallback)
    narrative: str    # The full, clean Markdown content
    tokens: int       # Estimated token count (GPT-4 tokenizer)
    chunks: List[Chunk] # Granular content blocks
```

### `Chunk`

```python
@dataclass
class Chunk:
    id: str
    content: str
    hash: str         # SHA256 integrity hash
    metadata: Dict    # Extra context (author, date)
```

---

## Advanced Usage

### 1. Targeted Retrieval (RAG Optimization)
Instead of fetching the entire page, ask for specific topics. The AIO server will filter chunks *before* sending them, saving bandwidth and context window.

```python
# Only get sections about "API Authentication"
envelope = parse("https://docs.stripe.com/api", query="authentication keys")

# 'narrative' now only contains relevant paragraphs
```

### 2. Integration with LangChain

```python
from langchain.document_loaders import BaseLoader
from aio_parser import parse

class AIOLoader(BaseLoader):
    def __init__(self, url):
        self.url = url
        
    def load(self):
        env = parse(self.url)
        return [Document(page_content=env.narrative, metadata={"source": "aio"})]
```

---

## Error Handling

The SDK raises specific exceptions for better control flow.

```python
from aio_parser.errors import (
    DiscoveryError,   # Could not find ANY content
    ValidationError,  # AIO JSON schema was invalid
    NetworkError      # Timeout or DNS failure
)
```

---

## Security Note

The parser automatically sanitizes output (Markdown) to prevent Markdown Injection attacks, but you should always treat retrieved content as **untrusted user input** before rendering it in a browser.

---

[Report Issue](https://github.com/aifusion/aio-parser/issues) | [View Source](../aio_parser/)
