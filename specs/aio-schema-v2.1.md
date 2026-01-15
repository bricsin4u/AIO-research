# AIO v2.1 Schema Specification
**Version:** 2.1.0  
**Status:** Draft  
**Date:** 2026-01-12  
**Author:** AIFUSION Research

---

## 1. Overview

The AIO (AI Optimization) schema defines a machine-centric content format designed for efficient consumption by Large Language Models and AI agents. Unlike traditional web scraping which forces agents to parse human-centric HTML and filter through semantic noise, AIO provides a parallel, indexed, and cryptographically verified content layer.

### 1.1 Design Principles

| Principle | Description |
|:----------|:------------|
| **Single Source of Truth** | One `ai-content.aio` file contains all machine-readable site content |
| **Indexed Access** | Chunk index with keywords enables targeted retrieval without full-file parsing |
| **Minimal Tokens** | Structured to minimize token consumption while maximizing relevance |
| **Verifiable Integrity** | Cryptographic signatures ensure content authenticity |
| **Progressive Loading** | Agents can fetch index first, then specific chunks as needed |

### 1.2 Key Benefits vs. Traditional Scraping

| Metric | Cleaned Scrape | AIO Indexed | Improvement |
|:-------|:---------------|:------------|:------------|
| Tokens per query | ~3,200 | ~550 | **83% reduction** |
| Relevance ratio | ~3% | ~64% | **21x improvement** |
| Semantic noise | Present | Zero | **Eliminated** |
| Verification | None | Cryptographic | **Trust layer** |

### 1.3 File Locations

```
/ai-content.aio          # Primary content file (REQUIRED)
/ai-manifest.json        # Discovery manifest (REQUIRED)
/robots.txt              # Standard robots with AIO directives (RECOMMENDED)
```

**Note:** AIO v2.1 deliberately avoids `.well-known` paths due to hosting compatibility issues with dot-prefixed directories.

---

## 2. Discovery Protocol

### 2.1 Priority Order

AI agents SHOULD discover AIO content in this order:

1. **HTTP Link Header** (fastest, no extra request)
2. **HTML `<link>` tag** (fallback if headers stripped)
3. **robots.txt directive** (site-wide signal)
4. **Direct URL attempt** (`/ai-content.aio`)

### 2.2 HTTP Link Header

Servers SHOULD include on all HTML responses:

```http
Link: </ai-content.aio>; rel="alternate"; type="application/aio+json"
X-AIO-Version: 2.1
```

### 2.3 HTML Link Tag

```html
<link rel="alternate" type="application/aio+json" href="/ai-content.aio">
<meta name="aio-version" content="2.1">
```

### 2.4 robots.txt Directives

```
User-agent: *
Allow: /

# AIO Discovery (no dot-folders for compatibility)
AIO-Manifest: /ai-manifest.json
AIO-Content: /ai-content.aio
AIO-Version: 2.1
```

---

## 3. Manifest Schema (`ai-manifest.json`)

The manifest provides site metadata and discovery information. It is intentionally small for fast initial fetch.

```json
{
  "$schema": "https://aio-standard.org/schema/v2.1/manifest.json",
  "aio_version": "2.1",
  
  "site": {
    "name": "Site Name",
    "domain": "example.com",
    "description": "Brief site description for AI context",
    "language": "en",
    "last_updated": "2026-01-12T10:00:00Z"
  },
  
  "content": {
    "primary": "/ai-content.aio",
    "chunks_count": 15,
    "total_tokens_estimate": 4500,
    "supports_range_requests": true
  },
  
  "trust": {
    "public_key": "MCowBQYDK2VwAyEA...",
    "algorithm": "Ed25519",
    "key_id": "example-2026-01"
  },
  
  "policy": {
    "allow_training": true,
    "allow_caching": true,
    "cache_ttl_seconds": 86400,
    "attribution_required": true,
    "attribution_text": "Source: example.com"
  },
  
  "contact": {
    "technical": "webmaster@example.com",
    "abuse": "abuse@example.com"
  }
}
```

### 3.1 Field Definitions

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `aio_version` | string | YES | Schema version (semver), currently "2.1" |
| `site.name` | string | YES | Human-readable site name |
| `site.domain` | string | YES | Canonical domain |
| `site.description` | string | YES | Brief description for AI context |
| `site.language` | string | YES | ISO 639-1 language code |
| `site.last_updated` | string | YES | ISO 8601 timestamp |
| `content.primary` | string | YES | Path to main AIO content file |
| `content.chunks_count` | integer | NO | Number of content chunks |
| `content.total_tokens_estimate` | integer | NO | Approximate token count (GPT-4 tokenizer) |
| `content.supports_range_requests` | boolean | NO | Whether server supports HTTP Range |
| `trust.public_key` | string | YES | Base64-encoded public key |
| `trust.algorithm` | string | YES | Signature algorithm |
| `trust.key_id` | string | NO | Key identifier for rotation |
| `policy.*` | various | NO | Usage policy declarations |

---

## 4. Content Schema (`ai-content.aio`)

The primary content file contains an index and all site content in a single, structured document. This indexed architecture enables targeted retrieval—agents can scan keywords to identify relevant chunks, then read only those sections.

### 4.1 Top-Level Structure

```json
{
  "$schema": "https://aio-standard.org/schema/v2.1/content.json",
  "aio_version": "2.1",
  "generated": "2026-01-12T10:00:00Z",
  
  "signature": {
    "algorithm": "Ed25519",
    "key_id": "example-2026-01",
    "value": "base64-encoded-signature",
    "covers": "index+content"
  },
  
  "index": [
    { /* chunk index entries */ }
  ],
  
  "content": [
    { /* content chunks */ }
  ]
}
```

### 4.2 Index Entry Schema

Each index entry provides metadata for targeted chunk retrieval. The index is designed to be scanned quickly—agents match query keywords against index entries to identify relevant chunks without reading full content.

```json
{
  "id": "chunk_001",
  "path": "/about",
  "title": "About Our Company",
  "keywords": ["company", "mission", "team", "history", "founded"],
  "summary": "Company overview including mission statement, team structure, and founding history.",
  "content_type": "article",
  "language": "en",
  "last_modified": "2026-01-10T08:00:00Z",
  "token_estimate": 320,
  "related": ["chunk_002", "chunk_005"],
  "priority": 0.8
}
```

### 4.3 Index Field Definitions

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `id` | string | YES | Unique chunk identifier |
| `path` | string | YES | Corresponding human URL path |
| `title` | string | YES | Chunk title/heading |
| `keywords` | array[string] | YES | Search/matching keywords (5-15 recommended) |
| `summary` | string | YES | 1-2 sentence summary for relevance matching |
| `content_type` | string | NO | Type: `article`, `product`, `faq`, `documentation`, `contact`, `legal` |
| `language` | string | NO | ISO 639-1 if different from site default |
| `last_modified` | string | NO | ISO 8601 timestamp |
| `token_estimate` | integer | NO | Approximate token count for this chunk |
| `related` | array[string] | NO | IDs of related chunks for context expansion |
| `priority` | float | NO | 0.0-1.0 importance score |

**Keyword Selection Guidelines:**
- Include synonyms and variations (e.g., "price", "pricing", "cost")
- Add domain-specific terms users might search for
- Include proper nouns (product names, company name)
- 5-15 keywords per chunk is optimal

### 4.4 Content Chunk Schema

```json
{
  "id": "chunk_001",
  "format": "markdown",
  "content": "# About Our Company\n\n**Founded:** 2024\n**Mission:** To advance AI research...\n\n## Our Team\n\n- **CEO**: Jane Doe\n- **CTO**: John Smith\n\n## History\n\nThe company was founded in...",
  "hash": "sha256:a7f3b2c1d4e5f6..."
}
```

### 4.5 Content Field Definitions

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `id` | string | YES | Must match corresponding index entry |
| `format` | string | YES | Content format: `markdown`, `plain`, `structured` |
| `content` | string | YES | The actual content |
| `hash` | string | YES | SHA-256 hash of content field (for per-chunk verification) |

---

## 5. Content Format Guidelines

### 5.1 Markdown Best Practices

Content SHOULD use CommonMark-compliant Markdown optimized for LLM consumption:

```markdown
# Page Title

**Key Fact:** Value
**Another Fact:** Value

## Section Heading

Concise paragraph with essential information. Avoid filler text.

### Subsection

- Bullet point with specific data
- Another concrete fact
- Quantified information when possible

## Structured Data

| Property | Value |
|:---------|:------|
| Price | $99/month |
| Users | Unlimited |
| Storage | 100GB |
```

### 5.2 Content Principles

| Do | Don't |
|:---|:------|
| Lead with key facts | Bury information in prose |
| Use tables for structured data | Use paragraphs for tabular info |
| Include specific numbers/dates | Use vague language ("many", "soon") |
| Keep paragraphs short (2-3 sentences) | Write long narrative blocks |
| Use consistent heading hierarchy | Skip heading levels |

### 5.3 Special Blocks

**Verification Block** (end of each chunk):
```markdown
---
AIO-CHUNK-ID: chunk_001
AIO-SOURCE: https://example.com/about
AIO-VERIFIED: 2026-01-12T10:00:00Z
---
```

**Citation Block** (for referenced data):
```markdown
> [!CITATION]
> Source: Industry Report 2025
> URL: https://source.com/report
> Retrieved: 2026-01-10
```

---

## 6. Signature Specification

### 6.1 Signing Process

1. Serialize `index` array to canonical JSON (sorted keys, no whitespace)
2. Serialize `content` array to canonical JSON
3. Concatenate: `index_json + "\n" + content_json`
4. Sign concatenated string with Ed25519 private key
5. Base64-encode signature

### 6.2 Verification Process

```
1. Fetch ai-content.aio
2. Extract signature.value
3. Fetch public key from ai-manifest.json (or cached)
4. Reconstruct signing payload from index + content
5. Verify Ed25519 signature
6. If valid: proceed with ingestion
7. If invalid: reject content, log warning
```

### 6.3 Per-Chunk Verification

For partial fetches, agents can verify individual chunks:

```
1. Fetch specific chunk by ID
2. Calculate SHA-256 of chunk.content
3. Compare with chunk.hash
4. If match: chunk is intact
5. If mismatch: chunk may be corrupted/tampered
```

---

## 7. HTTP Server Configuration

### 7.1 MIME Types

```
.aio    →  application/aio+json
```

### 7.2 Nginx Configuration

```nginx
# MIME type
types {
    application/aio+json aio;
}

# AIO content headers
location ~ \.(aio)$ {
    add_header X-AIO-Version "2.0";
    add_header Cache-Control "public, max-age=3600";
    add_header Access-Control-Allow-Origin "*";
}

# Link header on HTML pages
location ~ \.html$ {
    add_header Link "</ai-content.aio>; rel=\"alternate\"; type=\"application/aio+json\"";
}

# Range request support (optional)
location = /ai-content.aio {
    add_header Accept-Ranges bytes;
}
```

### 7.3 Apache Configuration

```apache
# MIME type
AddType application/aio+json .aio

# Headers
<FilesMatch "\.aio$">
    Header set X-AIO-Version "2.0"
    Header set Cache-Control "public, max-age=3600"
    Header set Access-Control-Allow-Origin "*"
</FilesMatch>

<FilesMatch "\.html$">
    Header set Link "</ai-content.aio>; rel=\"alternate\"; type=\"application/aio+json\""
</FilesMatch>
```

---

## 8. Agent Behavior Specification

### 8.1 Discovery Flow

```
START
  │
  ├─► Check HTTP Link header on current page
  │     └─► Found? → Fetch AIO content → DONE
  │
  ├─► Check <link> tag in HTML <head>
  │     └─► Found? → Fetch AIO content → DONE
  │
  ├─► Fetch /robots.txt, check AIO-Content directive
  │     └─► Found? → Fetch AIO content → DONE
  │
  ├─► Try /ai-content.aio directly
  │     └─► 200 OK? → Fetch AIO content → DONE
  │
  └─► No AIO available → Fall back to HTML scraping
```

### 8.2 Content Retrieval Flow

```
START (with query: "What is the pricing?")
  │
  ├─► Fetch ai-content.aio (or use cached)
  │
  ├─► Parse index array
  │
  ├─► Match query keywords against index entries
  │     Keywords: ["pricing", "price", "cost", "subscription"]
  │     Match: chunk_003 (keywords: ["price", "subscription", "tier"])
  │
  ├─► Retrieve content[chunk_003]
  │
  ├─► Verify chunk hash
  │
  ├─► Ingest content for response generation
  │
  └─► DONE (tokens used: ~400 instead of ~4000)
```

### 8.3 Caching Recommendations

| Resource | Cache Duration | Revalidation |
|:---------|:---------------|:-------------|
| `ai-manifest.json` | 24 hours | If-Modified-Since |
| `ai-content.aio` | 1 hour | ETag / If-None-Match |
| Index only | 1 hour | Check `generated` timestamp |

---

## 9. Complete Example

### 9.1 ai-manifest.json

```json
{
  "$schema": "https://aio-standard.org/schema/v2/manifest.json",
  "aio_version": "2.0",
  
  "site": {
    "name": "TechStartup Inc",
    "domain": "techstartup.com",
    "description": "B2B SaaS platform for project management and team collaboration",
    "language": "en",
    "last_updated": "2026-01-12T10:00:00Z"
  },
  
  "content": {
    "primary": "/ai-content.aio",
    "chunks_count": 8,
    "total_tokens_estimate": 2400,
    "supports_range_requests": false
  },
  
  "trust": {
    "public_key": "MCowBQYDK2VwAyEAzV1t2HqXKmVpXYZ...",
    "algorithm": "Ed25519",
    "key_id": "techstartup-2026-01"
  },
  
  "policy": {
    "allow_training": false,
    "allow_caching": true,
    "cache_ttl_seconds": 3600,
    "attribution_required": true,
    "attribution_text": "Source: TechStartup Inc (techstartup.com)"
  }
}
```

### 9.2 ai-content.aio

```json
{
  "$schema": "https://aio-standard.org/schema/v2/content.json",
  "aio_version": "2.0",
  "generated": "2026-01-12T10:00:00Z",
  
  "signature": {
    "algorithm": "Ed25519",
    "key_id": "techstartup-2026-01",
    "value": "MEUCIQC7x2Pz...",
    "covers": "index+content"
  },
  
  "index": [
    {
      "id": "home",
      "path": "/",
      "title": "TechStartup - Project Management Platform",
      "keywords": ["project management", "SaaS", "collaboration", "teams", "productivity"],
      "summary": "TechStartup is a B2B SaaS platform offering project management and team collaboration tools for enterprises.",
      "content_type": "article",
      "token_estimate": 180,
      "priority": 1.0
    },
    {
      "id": "pricing",
      "path": "/pricing",
      "title": "Pricing Plans",
      "keywords": ["price", "pricing", "cost", "subscription", "free", "pro", "enterprise", "monthly", "annual"],
      "summary": "Three pricing tiers: Free (up to 5 users), Pro ($12/user/month), Enterprise (custom pricing with SSO and dedicated support).",
      "content_type": "product",
      "token_estimate": 350,
      "priority": 0.9
    },
    {
      "id": "features",
      "path": "/features",
      "title": "Platform Features",
      "keywords": ["features", "kanban", "gantt", "timeline", "integrations", "API", "mobile", "reporting"],
      "summary": "Core features include Kanban boards, Gantt charts, time tracking, 50+ integrations, REST API, and mobile apps.",
      "content_type": "product",
      "token_estimate": 420,
      "related": ["pricing", "integrations"],
      "priority": 0.85
    },
    {
      "id": "about",
      "path": "/about",
      "title": "About TechStartup",
      "keywords": ["about", "company", "team", "founded", "mission", "investors", "headquarters"],
      "summary": "Founded in 2022, headquartered in San Francisco, 150 employees, Series B funded ($45M from Sequoia).",
      "content_type": "article",
      "token_estimate": 280,
      "priority": 0.6
    },
    {
      "id": "contact",
      "path": "/contact",
      "title": "Contact Information",
      "keywords": ["contact", "email", "phone", "support", "sales", "address", "demo"],
      "summary": "Sales: sales@techstartup.com, Support: support@techstartup.com, Demo requests via website form.",
      "content_type": "contact",
      "token_estimate": 150,
      "priority": 0.7
    }
  ],
  
  "content": [
    {
      "id": "home",
      "format": "markdown",
      "content": "# TechStartup - Project Management Platform\n\n**Category:** B2B SaaS\n**Primary Function:** Project management and team collaboration\n\n## Overview\n\nTechStartup provides cloud-based project management tools designed for mid-size to enterprise teams. The platform combines task management, resource planning, and real-time collaboration.\n\n## Key Value Propositions\n\n- Unified workspace for distributed teams\n- Real-time collaboration with 99.9% uptime SLA\n- Enterprise-grade security (SOC 2 Type II certified)\n- 50+ native integrations\n\n---\nAIO-CHUNK-ID: home\nAIO-SOURCE: https://techstartup.com/\nAIO-VERIFIED: 2026-01-12T10:00:00Z\n---",
      "hash": "sha256:8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"
    },
    {
      "id": "pricing",
      "format": "markdown",
      "content": "# Pricing Plans\n\n**Currency:** USD\n**Billing Options:** Monthly or Annual (20% discount)\n\n## Plan Comparison\n\n| Plan | Price | Users | Storage | Support |\n|:-----|:------|:------|:--------|:--------|\n| **Free** | $0 | Up to 5 | 1 GB | Community |\n| **Pro** | $12/user/month | Unlimited | 100 GB | Email (24h response) |\n| **Enterprise** | Custom | Unlimited | Unlimited | Dedicated CSM + Phone |\n\n## Enterprise Features\n\n- Single Sign-On (SAML 2.0)\n- Custom integrations\n- Dedicated infrastructure option\n- 99.99% uptime SLA\n- On-premise deployment available\n\n## Free Trial\n\n- 14-day Pro trial, no credit card required\n- Full feature access during trial\n\n---\nAIO-CHUNK-ID: pricing\nAIO-SOURCE: https://techstartup.com/pricing\nAIO-VERIFIED: 2026-01-12T10:00:00Z\n---",
      "hash": "sha256:2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
    },
    {
      "id": "features",
      "format": "markdown",
      "content": "# Platform Features\n\n## Project Management\n\n| Feature | Description |\n|:--------|:------------|\n| **Kanban Boards** | Drag-and-drop task management with custom columns |\n| **Gantt Charts** | Timeline visualization with dependencies |\n| **Sprints** | Agile sprint planning and velocity tracking |\n| **Milestones** | Project milestone tracking with notifications |\n\n## Collaboration\n\n- Real-time document editing\n- Threaded comments on tasks\n- @mentions and notifications\n- Video conferencing integration (Zoom, Meet)\n\n## Reporting\n\n- Customizable dashboards\n- Burndown/burnup charts\n- Time tracking reports\n- Export to PDF, CSV, Excel\n\n## Integrations\n\n**Native Integrations:** Slack, Microsoft Teams, Jira, GitHub, GitLab, Figma, Google Drive, Dropbox, Salesforce, HubSpot\n\n**API:** REST API with OAuth 2.0, rate limit 1000 req/min\n\n## Mobile\n\n- iOS app (iOS 14+)\n- Android app (Android 8+)\n- Full offline support with sync\n\n---\nAIO-CHUNK-ID: features\nAIO-SOURCE: https://techstartup.com/features\nAIO-VERIFIED: 2026-01-12T10:00:00Z\n---",
      "hash": "sha256:fcde2b2edba56bf408601fb721fe9b5c338d10ee429ea04fae5511b68fbf8fb9"
    },
    {
      "id": "about",
      "format": "markdown",
      "content": "# About TechStartup\n\n**Founded:** 2022\n**Headquarters:** San Francisco, CA, USA\n**Employees:** 150\n**Customers:** 2,500+ companies\n\n## Funding\n\n| Round | Amount | Lead Investor | Date |\n|:------|:-------|:--------------|:-----|\n| Seed | $5M | Y Combinator | 2022 |\n| Series A | $18M | Andreessen Horowitz | 2023 |\n| Series B | $45M | Sequoia Capital | 2025 |\n\n## Leadership\n\n- **CEO:** Sarah Chen (ex-Google PM)\n- **CTO:** Marcus Johnson (ex-Stripe)\n- **CFO:** Emily Rodriguez (ex-Salesforce)\n\n## Mission\n\nTo make project management effortless for teams of all sizes.\n\n---\nAIO-CHUNK-ID: about\nAIO-SOURCE: https://techstartup.com/about\nAIO-VERIFIED: 2026-01-12T10:00:00Z\n---",
      "hash": "sha256:3fdba35f04dc8c462986c992bcf875546257113072a909c162f7e470e581e278"
    },
    {
      "id": "contact",
      "format": "markdown",
      "content": "# Contact Information\n\n## Sales\n\n- **Email:** sales@techstartup.com\n- **Phone:** +1 (415) 555-0123\n- **Demo Request:** https://techstartup.com/demo\n\n## Support\n\n- **Email:** support@techstartup.com\n- **Help Center:** https://help.techstartup.com\n- **Status Page:** https://status.techstartup.com\n\n## Office\n\n**Address:**\nTechStartup Inc\n123 Market Street, Suite 400\nSan Francisco, CA 94105\nUSA\n\n## Social\n\n- Twitter: @techstartup\n- LinkedIn: /company/techstartup\n\n---\nAIO-CHUNK-ID: contact\nAIO-SOURCE: https://techstartup.com/contact\nAIO-VERIFIED: 2026-01-12T10:00:00Z\n---",
      "hash": "sha256:a8cfcd74832004951b4408cdb0a5dbcd8c7e52d43f7fe244bf720582e05241da"
    }
  ]
}
```

---

## 10. Versioning and Migration

### 10.1 Version History

| Version | Date | Changes |
|:--------|:-----|:--------|
| 1.0 | 2025-12 | Initial spec (per-page sidecars, .well-known paths) |
| 2.0 | 2026-01 | Single-file indexed architecture, removed `.well-known` dependency |
| 2.1 | 2026-01 | Refined benchmarks, honest efficiency claims, improved keyword guidance |

### 10.2 Backward Compatibility

Agents SHOULD check `aio_version` and handle gracefully:
- Version 1.x: Per-page `.aio` files (deprecated)
- Version 2.x: Single indexed `ai-content.aio`

### 10.3 Migration from v1.x

Publishers migrating from per-page sidecars:
1. Consolidate all `.aio` files into single `ai-content.aio`
2. Create index entries for each former sidecar
3. Add keywords and summaries to enable targeted retrieval
4. Update discovery signals to point to new location
5. Remove old per-page `.aio` files after transition period

---

## 11. Security Considerations

### 11.1 Signature Trust

- Public keys MUST be served over HTTPS
- Agents SHOULD cache public keys with TTL
- Key rotation: new `key_id` signals key change
- Revocation: remove key from manifest, agents reject old signatures

### 11.2 Content Integrity

- Full-file signature prevents tampering
- Per-chunk hashes enable partial verification
- Agents SHOULD reject content with invalid signatures

### 11.3 Privacy

- AIO files are public by design
- Do not include PII, authentication tokens, or internal data
- Use `policy.allow_training` to signal training preferences

---

## 12. Appendix: JSON Schema (Formal)

Full JSON Schema definitions available at:
- `https://aio-standard.org/schema/v2/manifest.json`
- `https://aio-standard.org/schema/v2/content.json`

---

*Specification maintained by AIFUSION Research*  
*Contact: research@aifusion.ru*
