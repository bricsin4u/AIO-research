# AIO Consumer Drivers (Parsers)

This directory contains the reference implementations of AIO-aware parsers and SDKs for various programming languages. These drivers enable AI agents to seamlessly consume AIO content or fall back to ECR-driven HTML cleaning.

## Available SDKs

| Language | Directory | Status | Features |
|:---|:---|:---|:---|
| **Python** | [`python/`](python/) | **Stable** | Full AIO discovery, fetching, ECR fallback, and pipeline support. |
| **Node.js** | [`nodejs/`](nodejs/) | **Beta** | AIO parsing and basic HTML cleaning. |
| **Go** | [`go/`](go/) | **Prototype** | Basic manifest discovery. |
| **Rust** | [`rust/`](rust/) | **Prototype** | High-performance manifest parsing. |
| **Java** | [`java/`](java/) | **Prototype** | Enterprise-grade parser template. |

---

## Python SDK Quick Start

The Python SDK is the most feature-complete implementation.

```python
from aio_core import AIOPipeline
from aio_parser import parse

# 1. High-level parsing
envelope = parse("https://example.com/pricing")
print(f"Content: {envelope.narrative}")

# 2. Detailed pipeline control
pipeline = AIOPipeline()
result = pipeline.process_html(raw_html, source_url="https://example.com")
print(f"Noise Score: {result.envelope.noise_score}")
```

## Node.js SDK Quick Start

```javascript
const { parse } = require('@aio/parser');

(async () => {
  const envelope = await parse('https://example.com');
  console.log(envelope.narrative);
})();
```

---

## Key Features

- **Auto-Discovery**: Detects AIO support via HTTP headers, HTML tags, or `robots.txt`.
- **ECR Fallback**: If AIO isn't available, the parser automatically applies **Entropy-Controlled Retrieval** logic to clean the HTML.
- **Unified Envelope**: All drivers return a standardized **Content Envelope** (JSON) with narrative, structure, and integrity layers.
- **Cryptographic Verification**: Ed25519 signature checks for AIO-optimized content.
