# AIO Agent Libraries

Libraries for AI agent developers to detect, extract, and verify AIO content.

## Overview

These libraries enable AI agents to:
1. **Detect** AIO-optimized pages
2. **Extract** clean Markdown content (avoiding HTML parsing noise)
3. **Verify** content authenticity via cryptographic signatures
4. **Trust** content based on verification status

## Quick Start

### Node.js

```bash
npm install cheerio tweetnacl
```

```javascript
const verifier = require('./aio-verifier');

// Extract from HTML
const result = verifier.extract(htmlContent);

// Or fetch and extract
const result = await verifier.fetchAndExtract('https://example.com/article');

// Check results
if (result.hasAIO) {
  console.log('Markdown:', result.markdown);
  console.log('Verified:', result.isVerified);
  console.log('Status:', result.trust.status);
}
```

### Python

```bash
pip install beautifulsoup4 requests pynacl
```

```python
from aio_verifier import AIOVerifier

verifier = AIOVerifier()

# Extract from HTML
result = verifier.extract(html_content)

# Or fetch and extract
result = verifier.fetch_and_extract('https://example.com/article')

# Check results
if result.has_aio:
    print('Markdown:', result.markdown)
    print('Verified:', result.is_verified)
    print('Status:', result.trust.status)
```

### REST API

Run the verification API:

```bash
node aio-verification-api.js
```

Then call it:

```bash
# Verify a URL
curl -X POST http://localhost:3000/verify-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# Extract from URL
curl "http://localhost:3000/extract?url=https://example.com/article"
```

## Verification Status Codes

| Status | Meaning | Trust Level |
|--------|---------|-------------|
| `VERIFIED` | Signature valid, content matches hash | ✅ High |
| `HASH_VALID` | No signature, but hash matches | ⚠️ Medium |
| `HASH_MISMATCH` | Content has been modified | ❌ None |
| `SIGNATURE_INVALID` | Signature check failed | ❌ None |
| `EXPIRED` | Timestamp too old | ⚠️ Low |
| `NO_TRUST_LAYER` | No verification metadata | ⚠️ Low |
| `NO_AIO_CONTENT` | No markdown shadow found | N/A |

## Response Structure

```javascript
{
  // Quick checks
  hasAIO: true,           // Has markdown shadow
  isVerified: true,       // Signature verified
  isTrusted: true,        // Verified OR hash valid
  
  // Content
  markdown: "---\ntitle: \"Title\"\ncitations:\n  - \"https://...\"\n---\n\n## Content...",
  jsonld: [{ "@type": "Article", ... }],
  
  // Trust details
  trust: {
    status: "VERIFIED",
    message: "Content verified - signature valid",
    hashValid: true,
    signatureValid: true,
    contentHash: "abc123...",
    timestamp: "2025-12-22T10:30:00Z",
    algorithm: "Ed25519",
    publicKey: "base64..."
  },
  
  // Page metadata
  meta: {
    title: "Page Title",
    description: "...",
    canonical: "https://..."
  }
}
```

## Integration Patterns

### Pattern 1: Prefer AIO, Fallback to HTML

```javascript
async function getContent(url) {
  const result = await verifier.fetchAndExtract(url);
  
  if (result.hasAIO && result.isTrusted) {
    // Use clean markdown
    return {
      content: result.markdown,
      source: 'aio',
      verified: result.isVerified
    };
  }
  
  // Fallback to HTML parsing
  return {
    content: parseHTML(result.rawHtml),
    source: 'html',
    verified: false
  };
}
```

### Pattern 2: Verification Required

```javascript
async function getVerifiedContent(url) {
  const result = await verifier.fetchAndExtract(url);
  
  if (!result.isVerified) {
    throw new Error(`Content not verified: ${result.trust.message}`);
  }
  
  return result.markdown;
}
```

### Pattern 3: Check Before Crawling

```javascript
async function shouldCrawl(url) {
  const instructions = await verifier.fetchAIInstructions(url);
  
  if (instructions?.policy?.allow_ai_indexing === false) {
    return false;
  }
  
  return true;
}
```

## Files

| File | Description |
|------|-------------|
| `aio-verifier.js` | Node.js verification library |
| `aio_verifier.py` | Python verification library |
| `aio-verification-api.js` | REST API service |

## Dependencies

### Node.js
- `cheerio` - HTML parsing (optional, falls back to regex)
- `tweetnacl` - Ed25519 verification (optional)

### Python
- `beautifulsoup4` - HTML parsing (optional)
- `requests` - HTTP fetching (optional)
- `pynacl` - Ed25519 verification (optional)

All dependencies are optional - the libraries work with reduced functionality without them.
