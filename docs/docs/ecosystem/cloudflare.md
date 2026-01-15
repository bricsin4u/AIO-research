# Cloudflare Worker AIO Adapter

**Type**: Serverless Edge Proxy  
**Cost**: Free Tier (100k req/day)  
**Best For**: Wix, Squarespace, Webflow, Carrd

This "Universal Adapter" sits in front of your website. It intercepts requests from AI bots and serves them clean JSON, while letting humans pass through to your normal visual site.

---

## Deployment Guide

### Prerequisites
- A Cloudflare Account.
- Your domain DNS managed by Cloudflare.
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/) installed (`npm install -g wrangler`).

### Step 1: Initialize
```bash
wrangler init aio-adapter
cd aio-adapter
```

### Step 2: Code
Copy `AIOv2/ecosystem/cloudflare-worker/worker.js` into `src/index.js`.

### Step 3: Configure
Edit `src/index.js` to point to your real site:
```javascript
const ORIGIN = "https://your-wix-site.com"; 
// Make sure this is the underlying URL if different, 
// or if using it as a router, the upstream.
```

### Step 4: Deploy
```bash
wrangler deploy
```
Cloudflare will give you a worker URL (e.g., `aio-adapter.yourname.workers.dev`).

### Step 5: Route Custom Domain (Optional but Recommended)
Go to **Cloudflare Dashboard > Workers > Triggers > Custom Domains**.
- Add `www.yoursite.com`.
- Now, all traffic to `www.yoursite.com` goes through the Worker.

---

## Verification

1.  **Visit Homepage**: `https://www.yoursite.com`. It should look normal (Proxied).
2.  **Inspect Headers**: Open DevTools > Network. Click the document request.
    - Check Response Headers for `Link`.
    - It should show: `Link: </ai-content.aio>; rel="alternate"...`
3.  **Visit AIO Endpoint**: `https://www.yoursite.com/ai-content.aio`.
    - It should show the JSON generated from your homepage.

---

## How the "Scraper" Works

The worker performs a "Self-Scrape" on request:
1.  Bot requests `.aio`.
2.  Worker fetches `ORIGIN/`.
3.  Worker uses Regex (lightweight) to extract `<title>` and `<body>`.
4.  Worker converts to Markdown.
5.  Worker responds with JSON.

**Limit**: By default, this only indexes the page you visit. To make it index the *whole site*, you would need to implement a crawler logic in the worker (complex) or use the worker to proxy a separate backend.
