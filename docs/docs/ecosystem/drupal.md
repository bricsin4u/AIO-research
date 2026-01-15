# Drupal AIO Module Guide

**Module Version**: `1.0`  
**Compatibility**: Drupal 9, 10, 11  
**License**: MIT

The Drupal module leverages the **Cache API** to serve high-performance AIO content suitable for enterprise and government sites.

---

## Installation

1.  **Manual Install**:
    - Create directory: `modules/custom/aio`.
    - Copy the 4 files from `AIOv2/ecosystem/drupal/` into it.
2.  **Enable Module**:
    ```bash
    drush en aio -y
    ```
    *Or via Admin > Extend.*
3.  **Rebuild Cache**:
    ```bash
    drush cr
    ```

---

## Verification

### 1. Test Endpoint
Visit `/ai-content.aio` on your site.
- You should receive a JSON response.
- Note the `X-Drupal-Cache` header; subsequent requests should be `HIT`.

### 2. Test Cache Invalidation
1.  Edit any Article node and save it.
2.  Refresh `/ai-content.aio`.
3.  The `modified` timestamp for that chunk should update instantly.

---

## Advanced Configuration

### Excluding Sensitivity Content
Government sites often have private nodes. The module uses `accessCheck(TRUE)`, so it **automatically respects** node permissions.
- If `Anonymous` cannot see a node, the AIO parser cannot see it either.

### Boosting Performance (Varnish)
The module adds the `node_list` cache tag.
- If you use Varnish/CDN, ensure your VCL respects `Surrogate-Keys`.
- This ensures the AIO file is cached at the edge but purged instantly when content changes.

### Customizing Output
To add custom fields (e.g., `field_summary` instead of body):

**File**: `src/Controller/AIOController.php`

```php
// In _aio_process_node function:
$summary = $node->get('field_summary')->value;
return [
  // ...
  'content' => "# " . $title . "\n\n" . $summary
];
```
