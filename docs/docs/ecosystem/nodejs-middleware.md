# Node.js Middleware

**Type**: Express/Connect Middleware  
**Path**: `ecosystem/nodejs/`

For custom Web Apps (Express, Next.js Custom Server, NestJS).

---

## Usage

```javascript
const aioAuto = require('./aio-express');
const app = express();

// 1. Configure the Crawler
app.use(aioAuto({
  baseUrl: 'http://localhost:3000', // Internal URL for scraping
  routes: ['/', '/pricing', '/features', '/docs'], // Routes to index
  manifest: { 
    site: { name: "My SaaS App" } 
  }
}));
```

---

## How it works (The "Self-Crawl")

Unlike the CMS plugins which read a database, this middleware **reads your rendered app**.

1.  When `/ai-content.aio` is requested...
2.  The middleware fires internal HTTP requests to `baseUrl + route`.
3.  It captures the HTML response (SSR).
4.  It uses `turndown` (included) to convert that HTML to Markdown.
5.  It constructs the JSON envelope.

**Benefit**: It works with *any* content your app renders, even if it comes from 3rd party APIs, databases, or hardcoded files.
