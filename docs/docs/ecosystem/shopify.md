# Shopify AIO Integration Guide

**Type**: Liquid Template Hack  
**Difficulty**: Easy (Copy & Paste)

Shopify allows creating custom `page` templates that render JSON instead of HTML. We abuse this feature to create a dynamic API.

---

## Installation Steps

1.  **Open Code Editor**:
    - Admin > Online Store > Themes > ... > Edit Code.

2.  **Create Template**:
    - Under **Templates**, click "Add a new template".
    - Type: `page`.
    - Suffix: `json`. (This creates `page.json.json` or `page.aio.json` depending on theme version, but we want `liquid` control).
    - **Better Method**: Create `page.aio-content.liquid`.

3.  **Paste Code**:
    - Copy content from `AIOv2/ecosystem/shopify/ai-content.liquid`.
    - Paste it into `page.aio-content.liquid`.
    - **Crucial**: Ensure `{% layout none %}` is at the very top. This stops Shopify from loading the theme header/footer.

4.  **Create the Endpoint**:
    - Go to **Pages**.
    - Create a page named "AI Content".
    - Assign Template: `aio-content` (suffix).
    - URL Handle: `ai-content`.

---

## Verification

Visit `https://yourstore.com/pages/ai-content`.

- **Success**: You see raw JSON text.
- **Fail (HTML)**: You see your site header/footer.
  - *Fix*: Ensure `{% layout none %}` is the first line of the liquid file.

---

## How it works

The Liquid code iterates through your `collections.all.products`.

```liquid
{% paginate collections.all.products by 1000 %}
  {% for product in collections.all.products %}
    ...
  {% endfor %}
{% endpaginate %}
```

**Limit**: Shopify limits pagination to 1000 items per page (usually 50, but up to 1000 in some contexts). If you have >1000 products, you may need to implement pagination logic in the parser (requesting `?page=2`).
