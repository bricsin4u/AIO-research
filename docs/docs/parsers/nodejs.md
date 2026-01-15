# Node.js AIO SDK Documentation

**Package**: `aio-parser-js`  
**Version**: `1.2.0`  
**License**: MIT

The Node.js SDK is designed for high-concurrency environments, making it ideal for web crawlers, real-time chatbots, and serverless functions (AWS Lambda, Cloudflare Workers).

---

## Installation

```bash
npm install aio-parser-js
# or
yarn add aio-parser-js
```

---

## Quick Start

```javascript
import { parse } from 'aio-parser-js';

async function fetchContent() {
  try {
    const data = await parse('https://example.com/blog/ai-future');
    
    console.log(`Source: ${data.source_type.toUpperCase()}`);
    console.log(data.narrative);
    
  } catch (error) {
    console.error('Failed to parse:', error.message);
  }
}
```

---

## Middleware Integration (Express.js)

The SDK provides a drop-in middleware pattern for easy integration.

```javascript
/* src/middleware/content.js */
const { parse } = require('aio-parser-js');

module.exports = async (req, res, next) => {
  const url = req.query.url;
  
  if (url) {
    const content = await parse(url);
    req.aio = content;
  }
  next();
};
```

---

## API Reference

### `parse(url: string, options?: ParseOptions): Promise<ContentEnvelope>`

#### `ParseOptions` Object
| Property | Type | Default | Description |
|:---|:---|:---|:---|
| `query` | string | `null` | Keywords for Targeted Retrieval |
| `timeout` | number | `5000` | Abort signal timeout (ms) |
| `headers` | object | `{}` | Custom headers (User-Agent, etc.) |
| `fallback` | boolean | `true` | Enable HTML scraping fallback |

#### Returns `ContentEnvelope`
```typescript
interface ContentEnvelope {
  id: string;
  source_type: 'aio' | 'scraped';
  narrative: string;
  tokens: number;
  noise_score: number; // 0.0 - 1.0
  chunks: Chunk[];
}
```

---

## Advanced Patterns

### 1. Concurrent Batch Processing
Node.js excels at processing multiple URLs simultaneously.

```javascript
const urls = ['https://site1.com', 'https://site2.com', 'https://site3.com'];

const results = await Promise.all(
  urls.map(url => parse(url).catch(e => ({ error: e.message })))
);
```

### 2. Streaming (Experimental)
For very large AIO files, use the streaming interface to process chunks as they arrive.

```javascript
import { parseStream } from 'aio-parser-js';

const stream = await parseStream('https://large-site.com');

stream.on('chunk', (chunk) => {
  console.log('Received chunk:', chunk.id);
});
```

---

## Troubleshooting

| Error Code | Meaning | Fix |
|:---|:---|:---|
| `ERR_NO_DISCOVERY` | No AIO signals found | Ensure `robots.txt` or `<link>` tags are present on the target. |
| `ERR_SCHEMA_INVALID` | JSON validation failed | The target's `.aio` file is malformed. |
| `ERR_TIMEOUT` | Request took too long | Increase `options.timeout`. |

---
[NPM Package](https://npmjs.com/package/aio-parser-js) | [Report Bug](https://github.com/aifusion/aio-parser-js)
