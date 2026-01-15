# WordPress AIO Integration Guide

**Plugin Version**: `2.0` (Auto-Sync)  
**Compatibility**: WordPress 5.8+  
**License**: MIT

The **AIO WordPress Plugin** is the "Gold Standard" implementation for publishers. It turns your WordPress database into a live AIO API without manual effort.

---

## Installation

1.  **Download Source**:
    - Get `aio-plugin.php` from `AIOv2/ecosystem/wordpress/`.
2.  **Upload to Server**:
    - Use SFTP or your Hosting File Manager.
    - Path: `/wp-content/plugins/aio-protocol/aio-plugin.php`
3.  **Activate**:
    - Go to **WP Admin > Plugins**.
    - Click **Activate** on "AIO Protocol Support".

---

## Verification

How to know it's working:

### 1. Check Discovery Signals
View the source of your homepage (`Ctrl+U`). You should see:
```html
<link rel="alternate" type="application/aio+json" href="https://yoursite.com/ai-content.aio" />
```

### 2. Check the API
Visit `https://yoursite.com/ai-content.aio` in your browser.
- **Success**: You see a JSON response starting with `{"$schema": "..."}`.
- **Failure**: You see a 404. (See Troubleshooting)

### 3. Test Robots.txt
Visit `https://yoursite.com/robots.txt`. It should contain:
```text
AIO-Content: https://yoursite.com/ai-content.aio
```

---

## Configuration

The plugin works out-of-the-box, but you can tweak it by editing the defined constants in `aio-plugin.php` (if we added them) or modifying the code directly.

### Support Custom Post Types
By default, only `post` is indexed. To add `products` or `events`:

1. Open `aio-plugin.php`.
2. Find the `WP_Query` arguments (approx line 85).
3. Change:
   ```php
   'post_type' => ['post', 'product', 'event'],
   ```

### Adjust Content Cleaning
If you want to keep some HTML tags (like `<table>`):

1. Modify the `strip_tags` logic.
   ```php
   $clean_text = strip_tags($content, '<table><tr><td><th>');
   ```

---

## Troubleshooting

### 404 Not Found on Endpoints
This is the most common issue. WordPress Rewrite Rules need flushing.
**Fix**: Go to **Settings > Permalinks** and simply click **Save Changes**. This forces WP to recognize the new `/ai-content.aio` route.

### "JSON Invalid" Error
If your JSON contains PHP warnings, it breaks validation.
**Fix**: Turn off `WP_DEBUG_DISPLAY` in your `wp-config.php`.
