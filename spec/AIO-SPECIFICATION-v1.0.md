# AIO (AI Optimization) Specification v1.0

**Status**: Published  
**Version**: 1.0.0  
**Date**: December 2025  
**Authors**: Igor Sergeevich Petrenko (AIFUSION Research)  

---

## Abstract

This document specifies the **AI Optimization (AIO)** standard — a methodology for web publishers to provide machine-optimized content layers that AI agents can extract, verify, and trust. AIO addresses the fundamental mismatch between human-centric HTML and the semantic extraction needs of Large Language Models (LLMs).

---

## 1. Introduction

### 1.1 Problem Statement

Modern web pages are optimized for visual rendering, not semantic extraction. When AI agents crawl web content, they encounter:

- Complex DOM structures with nested elements
- Advertising, navigation, and UI noise
- JavaScript-rendered content
- Ambiguous content boundaries

This results in:
- High token consumption for extraction
- Unreliable content parsing
- Potential hallucination from noisy input
- No mechanism to verify content authenticity

### 1.2 Solution Overview

AIO defines a four-layer system that publishers embed in their HTML:

| Layer | Purpose | Implementation |
|-------|---------|----------------|
| **Discovery** | Tell agents where to find AIO content | `/.well-known/ai-instructions.json`, `robots.txt` |
| **Structural** | Machine-readable entity data | JSON-LD (`application/ld+json`) |
| **Narrative** | Clean, extractable content | Markdown Shadow (`text/markdown`) |
| **Trust** | Cryptographic verification | Meta tags + signatures |

---

## 2. Conformance Requirements

The key words "MUST", "SHOULD", "MAY", "REQUIRED", "RECOMMENDED", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

### 2.1 Publisher Conformance Levels

| Level | Requirements |
|-------|--------------|
| **AIO Basic** | Narrative Layer (Markdown Shadow) |
| **AIO Standard** | Basic + Structural Layer (JSON-LD) + Discovery Layer |
| **AIO Verified** | Standard + Trust Layer (cryptographic signatures) |

### 2.2 Agent Conformance Levels

| Level | Requirements |
|-------|--------------|
| **AIO-Aware** | Can detect and extract Markdown Shadow |
| **AIO-Compliant** | Aware + respects Discovery Layer + extracts JSON-LD |
| **AIO-Verified** | Compliant + validates Trust Layer signatures |

---

## 3. Discovery Layer

### 3.1 AI Instructions File

Publishers SHOULD provide a JSON file at `/.well-known/ai-instructions.json`.

Additionally, publishers SHOULD include a link in the HTML `<head>` pointing to this file to ensure agents can discover it immediately upon visiting any page:

```html
<link rel="ai-instructions" href="/.well-known/ai-instructions.json">
```

**Schema:**

```json
{
  "$schema": "https://aio-standard.org/schema/v1/ai-instructions.json",
  "version": "1.0",
  "aio_version": "1.0.0",
  "publisher": {
    "name": "Publisher Name",
    "url": "https://example.com",
    "contact": "ai-support@example.com"
  },
  "policy": {
    "allow_ai_training": true,
    "allow_ai_indexing": true,
    "attribution_required": true,
    "commercial_use": "with_attribution"
  },
  "content": {
    "markdown_selector": "script[type='text/markdown']",
    "jsonld_selector": "script[type='application/ld+json']",
    "signature_meta": "aio-truth-signature",
    "default_language": "en"
  },
  "endpoints": {
    "sitemap": "/sitemap.xml",
    "api": "/api/aio/v1"
  }
}
```

**Required Fields:**
- `version`: Schema version (MUST be "1.0")
- `aio_version`: AIO specification version

**Optional Fields:**
- `publisher`: Publisher identification
- `policy`: Usage permissions for AI systems
- `content`: Selectors for AIO content
- `endpoints`: Additional API endpoints

### 3.2 Robots.txt Directives

Publishers SHOULD include AIO-specific directives in `robots.txt`:

```
# AIO Discovery
User-agent: *
Allow: /.well-known/ai-instructions.json

# AI Agent Permissions
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

# AIO Sitemap
Sitemap: https://example.com/sitemap.xml
```

---

## 4. Structural Layer (JSON-LD)

Publishers SHOULD include Schema.org structured data using JSON-LD format.

### 4.1 Placement

JSON-LD blocks MUST be placed within `<script type="application/ld+json">` tags in the document `<head>` or `<body>`.

### 4.2 Required Properties

For article content:

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Article Title",
  "author": {
    "@type": "Person",
    "name": "Author Name"
  },
  "datePublished": "2025-12-22",
  "description": "Brief description"
}
```

### 4.3 AIO Extensions

Publishers MAY include AIO-specific extensions:

```json
{
  "@context": ["https://schema.org", "https://aio-standard.org/context/v1"],
  "@type": "Article",
  "headline": "Article Title",
  "aio:contentHash": "sha256:abc123...",
  "aio:signatureAlgorithm": "Ed25519",
  "aio:verificationStatus": "signed"
}
```

---

## 5. Narrative Layer (Markdown Shadow)

The Narrative Layer provides a clean, token-efficient representation of page content.

### 5.1 Placement

The Markdown Shadow MUST be placed in a `<script>` tag with `type="text/markdown"`:

```html
<script type="text/markdown" id="aio-narrative-content">
# Article Title

**Author**: John Doe
**Date**: 2025-12-22

## Summary
Brief summary of the content.

## Content
Main article content in clean Markdown format.
</script>
```

### 5.2 Container Requirements

The script tag SHOULD be wrapped in a container with:
- `class="ai-only"` for CSS targeting
- `aria-hidden="true"` for accessibility
- `style="display:none"` to hide from visual rendering

```html
<section class="ai-only" aria-hidden="true" style="display:none!important">
  <script type="text/markdown" id="aio-narrative-content">
    ...
  </script>
</section>
```

### 5.3 Content Format

The Markdown content SHOULD follow this structure using YAML Frontmatter:

```markdown
---
title: "[Title]"
author: "[Author Name]"
date: "[ISO 8601 Date]"
url: "[Canonical URL]"
citations:
  - "[Reference URL 1]"
  - "[Reference URL 2]"
---

## Summary
[Executive summary, 1-3 sentences]

## Content
[Main content body]

## Key Points
- [Point 1]
- [Point 2]
```

### 5.4 Markdown Dialect

Content MUST use CommonMark-compliant Markdown. The following elements are RECOMMENDED:

- Headers (`#`, `##`, `###`)
- Bold (`**text**`)
- Italic (`*text*`)
- Links (`[text](url)`)
- Lists (`-` or `1.`)
- Code blocks (triple backticks)
- Blockquotes (`>`)

---

## 6. Trust Layer (Cryptographic Verification)

The Trust Layer enables AI agents to verify content authenticity and integrity.

### 6.1 Meta Tags

Publishers implementing the Trust Layer MUST include these meta tags:

```html
<meta name="aio-truth-signature" content="[signature]">
<meta name="aio-content-hash" content="[SHA-256 hash of markdown]">
<meta name="aio-public-key" content="[base64-encoded public key]">
<meta name="aio-last-verified" content="[ISO 8601 timestamp]">
<meta name="aio-signature-algorithm" content="[algorithm]">
```

### 6.2 Supported Algorithms

| Algorithm | Identifier | Key Size | Signature Size |
|-----------|------------|----------|----------------|
| Ed25519 | `Ed25519` | 32 bytes | 64 bytes |
| ECDSA P-256 | `ES256` | 32 bytes | 64 bytes |
| HMAC-SHA256 | `HS256` | 32+ bytes | 32 bytes |
| SHA-256 Hash Only | `SHA256-HASH` | N/A | 32 bytes |

**RECOMMENDED**: Ed25519 for asymmetric signing (allows public verification)  
**ACCEPTABLE**: HMAC-SHA256 for integrity checking (no public verification)  
**MINIMAL**: SHA256-HASH for basic integrity (hash only, no signature)

### 6.3 Signature Payload

The signature MUST be computed over a canonical JSON payload:

```json
{
  "content_hash": "[SHA-256 hash of trimmed markdown content]",
  "timestamp": "[ISO 8601 UTC timestamp]",
  "algorithm": "[algorithm identifier]"
}
```

**Canonicalization Rules:**
1. JSON keys MUST be sorted alphabetically
2. No whitespace between elements
3. UTF-8 encoding

**Example:**
```
{"algorithm":"Ed25519","content_hash":"abc123...","timestamp":"2025-12-22T10:30:00Z"}
```

### 6.4 Verification Process

AI agents SHOULD verify content using this process:

1. Extract Markdown Shadow content
2. Trim whitespace from content
3. Compute SHA-256 hash of trimmed content
4. Compare with `aio-content-hash` meta tag
5. If signature present:
   a. Reconstruct canonical payload
   b. Verify signature using public key
   c. Check timestamp is within acceptable range

### 6.5 Verification Results

Agents SHOULD classify verification results as:

| Status | Meaning |
|--------|---------|
| `VERIFIED` | Signature valid, content matches hash |
| `HASH_VALID` | No signature, but hash matches content |
| `HASH_MISMATCH` | Content has been modified |
| `SIGNATURE_INVALID` | Signature verification failed |
| `EXPIRED` | Timestamp outside acceptable range |
| `NO_TRUST_LAYER` | No verification metadata present |

---

## 7. HTTP Headers (Optional)

Publishers MAY also provide Trust Layer data via HTTP headers:

```
X-AIO-Content-Hash: sha256:abc123...
X-AIO-Signature: base64:xyz789...
X-AIO-Public-Key: base64:pubkey...
X-AIO-Timestamp: 2025-12-22T10:30:00Z
X-AIO-Algorithm: Ed25519
```

HTTP headers take precedence over meta tags if both are present.

---

## 8. API Endpoint (Optional)

Publishers MAY provide a REST API for programmatic access:

### 8.1 Get AIO Content

```
GET /api/aio/v1/content?url={page_url}
```

**Response:**
```json
{
  "url": "https://example.com/article",
  "markdown": "---\ntitle: \"Article Title\"\n---\n\n...",
  "jsonld": { "@context": "...", "@type": "Article", ... },
  "trust": {
    "signature": "base64:...",
    "contentHash": "sha256:...",
    "publicKey": "base64:...",
    "timestamp": "2025-12-22T10:30:00Z",
    "algorithm": "Ed25519",
    "status": "VERIFIED"
  }
}
```

### 8.2 Verify Content

```
POST /api/aio/v1/verify
Content-Type: application/json

{
  "markdown": "# Article content...",
  "signature": "base64:...",
  "publicKey": "base64:...",
  "timestamp": "2025-12-22T10:30:00Z"
}
```

**Response:**
```json
{
  "valid": true,
  "status": "VERIFIED",
  "contentHash": "sha256:...",
  "message": "Content verified successfully"
}
```

---

## 9. Security Considerations

### 9.1 Key Management

- Private keys MUST be stored securely and never exposed
- Public keys SHOULD be distributed via HTTPS
- Key rotation SHOULD occur at least annually
- Compromised keys SHOULD be revoked immediately

### 9.2 Replay Attacks

- Timestamps SHOULD be checked against a reasonable window (e.g., 24 hours for cached content)
- Agents MAY reject content with future timestamps

### 9.3 Content Injection

- Publishers MUST sanitize markdown content to prevent injection attacks
- Agents SHOULD treat markdown as untrusted input

### 9.4 Man-in-the-Middle

- AIO content SHOULD only be served over HTTPS
- Agents SHOULD verify TLS certificates

---

## 10. Privacy Considerations

### 10.1 Tracking

- AIO metadata SHOULD NOT contain user-identifying information
- Publishers SHOULD NOT use AIO for tracking purposes

### 10.2 Data Minimization

- Only necessary metadata SHOULD be included
- Personal data SHOULD be anonymized or excluded

---

## 11. Implementation Notes

### 11.1 For Publishers

1. Start with AIO Basic (Markdown Shadow only)
2. Add JSON-LD for better entity recognition
3. Implement signing for high-value content
4. Monitor AI agent access via server logs

### 11.2 For AI Agents

1. Check for `/.well-known/ai-instructions.json` first
2. Look for `<script type="text/markdown">` in page content
3. Fall back to HTML parsing if no AIO content found
4. Cache verification results to reduce computation

### 11.3 Graceful Degradation

- Agents MUST handle pages without AIO content
- Publishers MUST ensure pages work without AIO for human users
- Missing optional fields SHOULD NOT cause failures

---

## 12. IANA Considerations

### 12.1 Media Type Registration

This specification uses the following media type:

- `text/markdown` - For Markdown Shadow content (already registered)

### 12.2 Well-Known URI Registration

This specification requests registration of:

- `/.well-known/ai-instructions.json`

---

## 13. References

### 13.1 Normative References

- [RFC 2119] Key words for use in RFCs
- [RFC 8259] JSON Data Interchange Format
- [CommonMark] CommonMark Specification
- [Schema.org] Schema.org Vocabulary
- [RFC 8032] Edwards-Curve Digital Signature Algorithm (EdDSA)

### 13.2 Informative References

- [Petrenko 2025] "The Theory of Stupidity: A Formal Model of Cognitive Vulnerability"
- [AIO Academic Paper] "AI Optimization: A Technical Methodology for Cognitive Security"

---

## Appendix A: Complete Example

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Example Article</title>
    
    <!-- Structural Layer -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": "Understanding AI Optimization",
      "author": {"@type": "Person", "name": "Jane Doe"},
      "datePublished": "2025-12-22"
    }
    </script>
    
    <!-- Trust Layer -->
    <meta name="aio-truth-signature" content="MEUCIQDx...">
    <meta name="aio-content-hash" content="a1b2c3d4...">
    <meta name="aio-public-key" content="MCowBQYDK2VwAyEA...">
    <meta name="aio-last-verified" content="2025-12-22T10:30:00Z">
    <meta name="aio-signature-algorithm" content="Ed25519">
</head>
<body>
    <article>
        <h1>Understanding AI Optimization</h1>
        <p>Article content for human readers...</p>
    </article>
    
    <!-- Narrative Layer -->
    <section class="ai-only" aria-hidden="true" style="display:none!important">
        <script type="text/markdown" id="aio-narrative-content">
# Understanding AI Optimization

**Author**: Jane Doe
**Date**: 2025-12-22

## Summary
This article explains the AIO methodology for optimizing web content for AI agents.

## Content
AI Optimization (AIO) is a four-layer system that helps AI agents extract and verify web content efficiently...

---
AIO-VERSION: 1.0
        </script>
    </section>
</body>
</html>
```

---

## Appendix B: Changelog

### v1.0.0 (December 2025)
- Initial specification release

---

*This specification is released under CC BY 4.0 license.*
