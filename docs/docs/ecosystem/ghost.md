# Ghost CMS AIO Integration

**Type**: Theme Extension (Handlebars)  
**Path**: `ecosystem/ghost/`

---

## Installation

1.  **Download your active theme** (Settings > Design > Change Theme > Advanced > Download).
2.  **Unzip** the theme.
3.  **Add Files**:
    - Copy `ai-content.hbs` to the theme root.
    - Copy `ai-manifest.hbs` to the theme root.
4.  **Update Routes**:
    - Open `routes.yaml` (from Ghost settings or theme).
    - Add the AIO routes:
    ```yaml
    routes:
      /ai-content.aio/:
        template: ai-content
        content_type: application/json
      /ai-manifest.json/:
        template: ai-manifest
        content_type: application/json
    ```
5.  **Zip and Upload** the theme back to Ghost.

---

## Capabilities

Ghost's Content API is powerful. The Handlebars template iterates through **all posts**, updated in reverse chronological order.

- **Hash**: Dynamically generated.
- **Content**: Full HTML is included (Ghost `{{content}}` helper).
  - *Note*: Ideally, use a helper to strip HTML, but standard Ghost helpers render HTML. The AIO Parser (Consumer) will handle the Markdown conversion if needed, or you can use a client-side script in the template to strip it.
