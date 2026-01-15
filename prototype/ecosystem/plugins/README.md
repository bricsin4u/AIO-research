# AIO Publisher Ecosystem

**Turn any website into a Machine-Centric Architecture (MCA) source in minutes.**

This directory contains drop-in solutions for various CMS platforms and frameworks. These plugins enable publishers to host `.aio` files that are automatically generated and synchronized with their content.

---

## Available Integrations

### 1. Node.js (Express)
**Path:** [`nodejs/`](nodejs/)
A middleware that automatically generates AIO manifestations by crawling your local routes. Use it to provide AI-ready endpoints for your web applications.

### 2. WordPress
**Path:** [`wordpress/`](wordpress/)
A zero-config plugin that intercepts `/ai-content.aio` requests and serves fresh content directly from your WP database.

### 3. PHP (Generic)
**Path:** [`php/`](php/)
A helper library for Laravel, Symfony, or custom PHP applications to build AIO-compliant JSON responses.

### 4. Ghost CMS
**Path:** [`ghost/`](ghost/)
Theme-level templates to compile your posts into AIO format using Handlebars.

### 5. Shopify
**Path:** [`shopify/`](shopify/)
Liquid templates for e-commerce platforms to expose products and prices to AI agents.

### 6. Cloudflare Worker (Universal Adapter)
**Path:** [`cloudflare-worker/`](cloudflare-worker/)
**The "Magic" Solution:** A proxy worker that sits in front of *any* legacy site (Wix, Squarespace, Webflow) and injects AIO headers/content without touching the origin server.

---

## Usage Principles

- **Auto-Sync:** Content is generated on-demand or upon post-publish events.
- **Markdown-First:** All narrative content is stripped of HTML/CSS noise.
- **Factual Mapping:** Essential metadata (prices, dates) is extracted into the `structure` layer.

For detailed integration guides, navigate to the specific platform subdirectory.
