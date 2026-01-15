# AIO Ecosystem Guide

The AIO Ecosystem is a collection of "drop-in" tools that enable existing websites to support the AIO Protocol with zero or minimal code.

## Integration Matrix

| Platform | Type | Solution | Difficulty |
|:---|:---|:---|:---|
| **[WordPress](wordpress.md)** | `Plugin` | Native Plugin (`aio-plugin`) | Very Easy |
| **[Shopify](shopify.md)** | `Theme` | Liquid Template | Easy |
| **[Ghost](ghost.md)** | `Theme` | Handlebars Routes | Easy |
| **[Drupal](drupal.md)** | `Module` | AIO Module | Easy |
| **[Cloudflare](cloudflare.md)** | `Edge` | Worker Adapter | Moderate |
| **[Node.js](nodejs-middleware.md)** | `Middleware` | Express/Connect | Easy |
| **[MCP Server](../integrations/mcp-server.md)** | `AI Agent` | Claude Desktop / Cursor | Easy |

---

## Which tool should I use?

### 1. "I have a CMS"
Use the native plugins for [WordPress](wordpress.md) or [Drupal](drupal.md). They integrate deeply with your database and update content in real-time.

### 2. "I effectively rent my site (SaaS)"
If you use **Wix**, **Squarespace**, **Webflow**, or **Shopify**, you cannot easily run backend code.
- **Option A**: Use [Shopify](shopify.md) templates if supported.
- **Option B (Universal)**: Use the [Cloudflare Worker](cloudflare.md) adapter. It sits *in front* of your site and adds AIO support to *any* platform.

### 3. "I built a custom app"
Use the [Node.js Middleware](nodejs-middleware.md) for Express/Next.js apps, or implement the protocol manually using our [SDKs](../parsers/).
