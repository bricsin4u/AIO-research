# AIO Integration Guide
## For Developers & Content Teams

This guide explains how to integrate AIO signing into your workflow.

---

## Available Libraries

| Platform | File | Requirements |
|----------|------|--------------|
| **WordPress** | `lib/wordpress/aio-signing-plugin.php` | WordPress 5.0+ |
| **Drupal** | `lib/drupal/aio_signing.module` | Drupal 9/10 |
| **Laravel** | `lib/laravel/` | Laravel 8+ |
| **Strapi** | `lib/strapi/aio-middleware.js` | Strapi v4 |
| **Contentful** | `lib/contentful/aio-contentful.js` | Any frontend |
| **Ghost** | `lib/ghost/aio-helper.js` | Ghost 5+ |
| **Shopify** | `lib/shopify/aio-snippet.liquid` | Shopify 2.0 themes |
| **Next.js/React** | `lib/react/AIOProvider.jsx` | React 16.8+ |
| **Node.js** | `lib/aio-signing.js` | Node 16+ |
| **PHP** | `lib/aio-signing.php` | PHP 7.2+ |
| **Python CLI** | `aio_cli.py` | Python 3.8+ |

---

## WordPress (Easiest)

Just install the plugin - no coding required!

1. Copy `lib/wordpress/aio-signing-plugin.php` to `wp-content/plugins/aio-signing/`
2. Activate in WordPress Admin → Plugins
3. Go to Settings → AIO Signing
4. Click "Generate Keys"
5. Save

Done! All your posts and pages are now automatically signed.

---

## Drupal 9/10

1. Create folder: `modules/custom/aio_signing/`
2. Copy `lib/drupal/aio_signing.module` and `lib/drupal/aio_signing.info.yml`
3. Enable: `drush en aio_signing`
4. Configure at `/admin/config/content/aio-signing`

The module auto-signs all nodes (articles, pages) on render.

---

## Laravel

1. Copy files from `lib/laravel/` to your app:
   - `AIOSigning.php` → `app/Services/`
   - `AIOServiceProvider.php` → `app/Providers/`
   - `AIOMiddleware.php` → `app/Http/Middleware/`

2. Register provider in `config/app.php`:
```php
'providers' => [
    App\Providers\AIOServiceProvider::class,
],
```

3. Add to `.env`:
```
AIO_PRIVATE_KEY=your_key_here
AIO_PUBLIC_KEY=your_key_here
```

4. Use in Blade templates:
```blade
<head>
    @aioHead($markdown)
</head>
<body>
    {{-- Your content --}}
    @aioShadow($markdown)
</body>
```

Or use the middleware for automatic injection.

---

## Strapi v4

1. Copy `lib/strapi/aio-middleware.js` to `src/middlewares/`

2. Register in `config/middlewares.js`:
```javascript
module.exports = [
  // ... other middlewares
  {
    name: 'global::aio-signing',
    config: {
      alwaysInclude: true, // or false to require ?aio=true
    },
  },
];
```

3. Add to `.env`:
```
AIO_PRIVATE_KEY=your_key
AIO_PUBLIC_KEY=your_key
```

API responses will include `aio` object with markdown and signature.

---

## Contentful (Headless)

Contentful is API-only, so you sign on your frontend:

```javascript
import { signContentfulEntry, generateMetaTags, generateShadow } from './lib/contentful/aio-contentful';

// In getStaticProps or getServerSideProps
const entry = await contentfulClient.getEntry('xxx');
const aio = signContentfulEntry(entry, {
  titleField: 'title',
  bodyField: 'content',
  privateKey: process.env.AIO_PRIVATE_KEY,
  publicKey: process.env.AIO_PUBLIC_KEY,
});

// In your component
<Head>
  <div dangerouslySetInnerHTML={{ __html: generateMetaTags(aio) }} />
</Head>
<div dangerouslySetInnerHTML={{ __html: generateShadow(aio.markdown) }} />
```

---

## Ghost

### Option A: Code Injection (No theme changes)

Go to Ghost Admin → Settings → Code Injection → Site Header, paste the script from `lib/ghost/aio-helper.js`.

### Option B: Custom Theme

Add partials to your theme:
- `partials/aio-head.hbs` 
- `partials/aio-shadow.hbs`

See `lib/ghost/aio-helper.js` for template code.

---

## Shopify

1. Copy `lib/shopify/aio-snippet.liquid` to your theme's `snippets/` folder

2. In `theme.liquid`, add before `</head>`:
```liquid
{% include 'aio-snippet', type: 'head' %}
```

3. Before `</body>`:
```liquid
{% include 'aio-snippet', type: 'shadow' %}
```

For product pages:
```liquid
{% include 'aio-snippet', type: 'shadow', product: product %}
```

Note: Shopify Liquid can't do cryptographic signing. For full signing, use a Shopify app or edge function.

---

## PHP (Laravel, Symfony, Custom)

```php
require_once 'lib/aio-signing.php';

// Generate keys once, save to .env
// php lib/aio-signing.php generate-keys

$privateKey = getenv('AIO_PRIVATE_KEY');
$publicKey = getenv('AIO_PUBLIC_KEY');

// Your content
$markdown = "# My Article\n\nContent here...";

// Sign and inject into HTML
$html = AIO::injectAIOLayer($html, $markdown, $privateKey, $publicKey);
```

### Laravel Middleware

```php
// app/Http/Kernel.php
protected $middleware = [
    // ...
    AIO::laravelMiddleware(),
];
```

---

## Node.js / Express

```javascript
const aio = require('./lib/aio-signing');

// Generate keys once
const keys = aio.generateKeys();
console.log('Save these to .env:', keys);

// In your route
app.get('/article/:id', (req, res) => {
    const article = getArticle(req.params.id);
    const markdown = `# ${article.title}\n\n${article.content}`;
    
    let html = renderTemplate(article);
    html = aio.injectAIOLayer(html, markdown, keys);
    
    res.send(html);
});
```

### Express Middleware

```javascript
const aio = require('./lib/aio-signing');

app.use(aio.middleware({
    privateKey: process.env.AIO_PRIVATE_KEY,
    publicKey: process.env.AIO_PUBLIC_KEY,
    getMarkdown: (req) => req.aioMarkdown // Set this in your routes
}));
```

---

## Next.js / React

```jsx
// pages/blog/[slug].jsx
import Head from 'next/head';
import { AIOShadow } from '../../lib/react/AIOProvider';

export async function getServerSideProps({ params }) {
    const post = await fetchPost(params.slug);
    const markdown = `# ${post.title}\n\n${post.content}`;
    
    // Sign server-side
    const crypto = require('crypto');
    const contentHash = crypto.createHash('sha256').update(markdown).digest('hex');
    const timestamp = new Date().toISOString();
    
    return {
        props: {
            post,
            markdown,
            aio: { contentHash, timestamp, publicKey: process.env.AIO_PUBLIC_KEY }
        }
    };
}

export default function BlogPost({ post, markdown, aio }) {
    return (
        <>
            <Head>
                <meta name="aio-content-hash" content={aio.contentHash} />
                <meta name="aio-public-key" content={aio.publicKey} />
                <meta name="aio-last-verified" content={aio.timestamp} />
            </Head>
            
            <article>
                <h1>{post.title}</h1>
                <div dangerouslySetInnerHTML={{ __html: post.html }} />
            </article>
            
            <AIOShadow markdown={markdown} />
        </>
    );
}
```

See `lib/react/next-example.jsx` for complete example.

---

## Static Sites (Python CLI)

For Jekyll, Hugo, Eleventy, or plain HTML:

```bash
# First time only
python aio_cli.py setup

# After building your site
python aio_cli.py sign

# Or watch for changes during development
python aio_cli.py watch
```

### Build Script Integration

```json
// package.json
{
  "scripts": {
    "build": "hugo && python aio_cli.py sign",
    "dev": "hugo serve & python aio_cli.py watch"
  }
}
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/sign-content.yml
name: Sign AIO Content

on:
  push:
    paths: ['**.html']

jobs:
  sign:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install cryptography beautifulsoup4
      - run: |
          mkdir -p .aio-keys
          echo "${{ secrets.AIO_PRIVATE_KEY }}" > .aio-keys/private_key.pem
      - run: python aio_cli.py sign
      - run: |
          git config user.name "AIO Bot"
          git add *.html
          git commit -m "🔏 Sign content" || true
          git push
```

### Netlify / Vercel

Add to your build command:
```bash
npm run build && python aio_cli.py sign
```

---

## Key Management

### Generate Keys

**PHP:**
```bash
php lib/aio-signing.php generate-keys
```

**Node.js:**
```javascript
const aio = require('./lib/aio-signing');
console.log(aio.generateKeys());
```

**Python:**
```bash
python aio_cli.py setup
```

### Store Keys Securely

- **Local dev**: `.env` file (add to `.gitignore`)
- **Production**: Environment variables or secrets manager
- **WordPress**: Database (encrypted by plugin)

### DO:
- ✅ Back up private key securely
- ✅ Use different keys per project
- ✅ Rotate keys annually

### DON'T:
- ❌ Commit private key to git
- ❌ Share private key
- ❌ Use same key across unrelated sites

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No markdown shadow found" | Add `<script type="text/markdown">` block |
| "Signature verification failed" | Re-sign after content changes |
| "No signing keys found" | Run key generation for your platform |
| PHP sodium error | Upgrade to PHP 7.2+ or install sodium extension |
| Node.js tweetnacl error | Run `npm install tweetnacl tweetnacl-util` |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Your Website                          │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Content   │  │  Markdown   │  │    Signing      │ │
│  │   (HTML)    │→ │  Generator  │→ │    Library      │ │
│  └─────────────┘  └─────────────┘  └────────┬────────┘ │
│                                              │          │
│  ┌───────────────────────────────────────────▼────────┐ │
│  │              Final HTML Output                      │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │ <head>                                        │  │ │
│  │  │   <meta name="aio-truth-signature" ...>      │  │ │
│  │  │   <meta name="aio-content-hash" ...>         │  │ │
│  │  │   <meta name="aio-public-key" ...>           │  │ │
│  │  │ </head>                                       │  │ │
│  │  │ <body>                                        │  │ │
│  │  │   [Your visible content]                      │  │ │
│  │  │   <section class="ai-only">                   │  │ │
│  │  │     <script type="text/markdown">             │  │ │
│  │  │       [Markdown shadow]                       │  │ │
│  │  │     </script>                                 │  │ │
│  │  │   </section>                                  │  │ │
│  │  │ </body>                                       │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Support

- Theory: `manuscript_en.md`
- Implementation: `IMPLEMENTATION.md`
- Academic Paper: `AIO_Academic_Paper.md`


---

## For AI Agent Developers

If you're building an AI agent, crawler, or search system, use the verification libraries:

### Node.js Agent

```javascript
const verifier = require('./lib/agent/aio-verifier');

const result = await verifier.fetchAndExtract('https://example.com/article');

if (result.hasAIO && result.isTrusted) {
  // Use clean markdown instead of parsing HTML
  console.log(result.markdown);
  console.log('Verified:', result.isVerified);
}
```

### Python Agent

```python
from lib.agent.aio_verifier import AIOVerifier

verifier = AIOVerifier()
result = verifier.fetch_and_extract('https://example.com/article')

if result.has_aio and result.is_trusted:
    print(result.markdown)
    print('Verified:', result.is_verified)
```

### REST API

Deploy `lib/agent/aio-verification-api.js` and call:

```bash
curl "http://your-api/extract?url=https://example.com/article"
```

See `lib/agent/README.md` for full documentation.

---

## Specification

The formal AIO specification is available at `spec/AIO-SPECIFICATION-v1.0.md`.

This document defines:
- Discovery Layer (ai-instructions.json, robots.txt)
- Structural Layer (JSON-LD)
- Narrative Layer (Markdown Shadow)
- Trust Layer (cryptographic signatures)
- Verification process for AI agents
- Conformance levels for publishers and agents
