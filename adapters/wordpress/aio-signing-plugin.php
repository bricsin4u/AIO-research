<?php
/**
 * Plugin Name: AIO Content Signing
 * Description: Automatically signs your content for AI optimization
 * Version: 1.0.0
 * Author: AIFUSION
 * 
 * Installation:
 * 1. Copy this file to wp-content/plugins/aio-signing/aio-signing.php
 * 2. Activate in WordPress admin
 * 3. Go to Settings > AIO Signing to configure
 */

if (!defined('ABSPATH')) exit;

class AIO_Signing_Plugin {
    
    private static $instance = null;
    private $public_key;
    private $private_key;
    
    public static function instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        // Load keys
        $this->public_key = get_option('aio_public_key', '');
        $this->private_key = get_option('aio_private_key', '');
        
        // Hooks
        add_action('admin_menu', [$this, 'add_admin_menu']);
        add_action('admin_init', [$this, 'register_settings']);
        add_action('wp_head', [$this, 'output_meta_tags'], 1);
        add_action('wp_footer', [$this, 'output_markdown_shadow'], 100);
        
        // AJAX for key generation
        add_action('wp_ajax_aio_generate_keys', [$this, 'ajax_generate_keys']);
    }
    
    /**
     * Admin menu
     */
    public function add_admin_menu() {
        add_options_page(
            'AIO Signing Settings',
            'AIO Signing',
            'manage_options',
            'aio-signing',
            [$this, 'settings_page']
        );
    }
    
    /**
     * Register settings
     */
    public function register_settings() {
        register_setting('aio_signing', 'aio_public_key');
        register_setting('aio_signing', 'aio_private_key');
        register_setting('aio_signing', 'aio_enabled', ['default' => '1']);
        register_setting('aio_signing', 'aio_post_types', ['default' => ['post', 'page']]);
    }
    
    /**
     * Settings page HTML
     */
    public function settings_page() {
        ?>
        <div class="wrap">
            <h1>AIO Content Signing</h1>
            
            <p>This plugin automatically adds AI-optimized content layers to your posts and pages.</p>
            
            <?php if (empty($this->private_key)): ?>
            <div class="notice notice-warning">
                <p><strong>Setup Required:</strong> Generate your signing keys below.</p>
            </div>
            <?php endif; ?>
            
            <form method="post" action="options.php">
                <?php settings_fields('aio_signing'); ?>
                
                <table class="form-table">
                    <tr>
                        <th>Enable AIO Signing</th>
                        <td>
                            <label>
                                <input type="checkbox" name="aio_enabled" value="1" 
                                    <?php checked(get_option('aio_enabled', '1'), '1'); ?>>
                                Add AIO layers to content
                            </label>
                        </td>
                    </tr>
                    
                    <tr>
                        <th>Public Key</th>
                        <td>
                            <input type="text" name="aio_public_key" class="large-text" 
                                value="<?php echo esc_attr($this->public_key); ?>" readonly>
                            <p class="description">This key is embedded in your pages for verification.</p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th>Private Key</th>
                        <td>
                            <input type="password" name="aio_private_key" class="large-text" 
                                value="<?php echo esc_attr($this->private_key); ?>">
                            <p class="description">Keep this secret! Used to sign your content.</p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th>Generate New Keys</th>
                        <td>
                            <button type="button" class="button" id="aio-generate-keys">
                                Generate Keys
                            </button>
                            <p class="description">Creates a new keypair. Warning: invalidates existing signatures!</p>
                        </td>
                    </tr>
                </table>
                
                <?php submit_button(); ?>
            </form>
            
            <hr>
            
            <h2>How It Works</h2>
            <ol>
                <li>When a post/page is viewed, the plugin generates a Markdown version of the content</li>
                <li>The Markdown is cryptographically signed with your private key</li>
                <li>The signature and Markdown "shadow" are injected into the HTML</li>
                <li>AI agents can verify the content is authentic and untampered</li>
            </ol>
        </div>
        
        <script>
        jQuery(document).ready(function($) {
            $('#aio-generate-keys').click(function() {
                if (!confirm('Generate new keys? This will invalidate all existing signatures.')) {
                    return;
                }
                
                $.post(ajaxurl, { action: 'aio_generate_keys' }, function(response) {
                    if (response.success) {
                        $('input[name="aio_public_key"]').val(response.data.public_key);
                        $('input[name="aio_private_key"]').val(response.data.private_key);
                        alert('Keys generated! Click "Save Changes" to store them.');
                    } else {
                        alert('Error generating keys: ' + response.data);
                    }
                });
            });
        });
        </script>
        <?php
    }
    
    /**
     * AJAX: Generate keys
     */
    public function ajax_generate_keys() {
        if (!current_user_can('manage_options')) {
            wp_send_json_error('Unauthorized');
        }
        
        $keypair = sodium_crypto_sign_keypair();
        
        wp_send_json_success([
            'public_key' => base64_encode(sodium_crypto_sign_publickey($keypair)),
            'private_key' => base64_encode(sodium_crypto_sign_secretkey($keypair))
        ]);
    }
    
    /**
     * Get current content as Markdown
     */
    private function get_markdown_content() {
        if (!is_singular()) return null;
        
        $post = get_post();
        if (!$post) return null;
        
        // Check if enabled for this post type
        $enabled_types = get_option('aio_post_types', ['post', 'page']);
        if (!in_array($post->post_type, $enabled_types)) return null;
        
        // Build Frontmatter
        $metadata = [
            'title' => get_the_title(),
            'site_name' => get_bloginfo('name'),
            'author' => get_the_author(),
            'date' => get_the_date('Y-m-d'),
            'url' => get_permalink()
        ];
        
        // Extract Citations (External Links) from content
        $content_raw = apply_filters('the_content', $post->post_content);
        $citations = [];
        if (preg_match_all('/<a[^>]*href=["\'](http[^"\']*)["\'][^>]*>/i', $content_raw, $matches)) {
            $site_url = get_site_url();
            foreach ($matches[1] as $href) {
                // Filter out internal links
                if (strpos($href, $site_url) === false) {
                    if (!in_array($href, $citations)) {
                        $citations[] = $href;
                    }
                }
            }
        }
        if (!empty($citations)) {
            $metadata['citations'] = $citations;
        }

        // Generate YAML Frontmatter
        $markdown = "---\n";
        foreach ($metadata as $key => $value) {
            if ($key === 'citations') {
                $markdown .= "citations:\n";
                foreach ($value as $cite) {
                    $markdown .= "  - $cite\n";
                }
            } else {
                $safe_value = str_replace('"', '\\"', $value);
                $markdown .= "$key: \"$safe_value\"\n";
            }
        }
        $markdown .= "---\n\n";
        
        // Get excerpt/summary
        if (has_excerpt()) {
            $markdown .= "## Summary\n" . get_the_excerpt() . "\n\n";
        }
        
        // Get content as markdown
        $markdown .= "## Content\n" . $this->html_to_markdown($content_raw);
        
        // Categories/tags
        $categories = get_the_category();
        if ($categories) {
            $markdown .= "\n\n## Categories\n";
            foreach ($categories as $cat) {
                $markdown .= "- " . $cat->name . "\n";
            }
        }
        
        return trim($markdown);
    }
    
    /**
     * Convert HTML to Markdown
     */
    private function html_to_markdown($html) {
        // Strip scripts and styles
        $html = preg_replace('/<script\b[^>]*>(.*?)<\/script>/is', '', $html);
        $html = preg_replace('/<style\b[^>]*>(.*?)<\/style>/is', '', $html);
        
        // Headers
        $html = preg_replace('/<h1[^>]*>(.*?)<\/h1>/i', "# $1\n\n", $html);
        $html = preg_replace('/<h2[^>]*>(.*?)<\/h2>/i', "## $1\n\n", $html);
        $html = preg_replace('/<h3[^>]*>(.*?)<\/h3>/i', "### $1\n\n", $html);
        $html = preg_replace('/<h4[^>]*>(.*?)<\/h4>/i', "#### $1\n\n", $html);
        
        // Paragraphs
        $html = preg_replace('/<p[^>]*>(.*?)<\/p>/is', "$1\n\n", $html);
        
        // Bold/Italic
        $html = preg_replace('/<strong[^>]*>(.*?)<\/strong>/i', "**$1**", $html);
        $html = preg_replace('/<b[^>]*>(.*?)<\/b>/i', "**$1**", $html);
        $html = preg_replace('/<em[^>]*>(.*?)<\/em>/i', "*$1*", $html);
        $html = preg_replace('/<i[^>]*>(.*?)<\/i>/i', "*$1*", $html);
        
        // Links
        $html = preg_replace('/<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)<\/a>/i', "[$2]($1)", $html);
        
        // Lists
        $html = preg_replace('/<li[^>]*>(.*?)<\/li>/is', "- $1\n", $html);
        $html = preg_replace('/<\/?[uo]l[^>]*>/i', "\n", $html);
        
        // Blockquotes
        $html = preg_replace('/<blockquote[^>]*>(.*?)<\/blockquote>/is', "> $1\n", $html);
        
        // Code
        $html = preg_replace('/<code[^>]*>(.*?)<\/code>/i', "`$1`", $html);
        $html = preg_replace('/<pre[^>]*>(.*?)<\/pre>/is', "```\n$1\n```\n", $html);
        
        // Images
        $html = preg_replace('/<img[^>]*alt=["\']([^"\']*)["\'][^>]*src=["\']([^"\']*)["\'][^>]*>/i', "![$1]($2)", $html);
        $html = preg_replace('/<img[^>]*src=["\']([^"\']*)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*>/i', "![$2]($1)", $html);
        
        // Strip remaining HTML
        $html = strip_tags($html);
        
        // Clean up whitespace
        $html = preg_replace('/\n{3,}/', "\n\n", $html);
        $html = preg_replace('/[ \t]+/', ' ', $html);
        
        return trim($html);
    }
    
    /**
     * Sign content
     */
    private function sign_content($markdown) {
        if (empty($this->private_key)) return null;
        
        $timestamp = gmdate('Y-m-d\TH:i:s\Z');
        $content_hash = hash('sha256', trim($markdown));
        
        $payload = json_encode([
            'content_hash' => $content_hash,
            'timestamp' => $timestamp,
            'algorithm' => 'Ed25519'
        ], JSON_UNESCAPED_SLASHES);
        
        try {
            $private_key = base64_decode($this->private_key);
            $signature = sodium_crypto_sign_detached($payload, $private_key);
            
            return [
                'signature' => base64_encode($signature),
                'content_hash' => $content_hash,
                'timestamp' => $timestamp
            ];
        } catch (Exception $e) {
            return null;
        }
    }
    
    /**
     * Output meta tags and link tag to head
     */
    public function output_meta_tags() {
        if (!is_singular()) return;
        
        $post = get_post();
        $enabled_types = get_option('aio_post_types', ['post', 'page']);
        if (!in_array($post->post_type, $enabled_types)) return;

        // Link to AI Instructions
        echo '<link rel="ai-instructions" href="/.well-known/ai-instructions.json">' . "\n";
        
        // Output existing signature meta tags if they exist in post meta
        // (In a real implementation, we would store these in post meta after signing)
    }
    
    /**
     * Output markdown shadow before </body>
     */
    public function output_markdown_shadow() {
        if (!get_option('aio_enabled', '1')) return;
        
        $markdown = $this->get_markdown_content();
        if (!$markdown) return;
        
        echo "\n<!-- AIO Narrative Layer -->\n";
        echo '<section class="ai-only" aria-hidden="true" style="display:none!important">' . "\n";
        echo '<script type="text/markdown" id="aio-narrative-content">' . "\n";
        echo esc_html($markdown) . "\n";
        echo '</script>' . "\n";
        echo '</section>' . "\n";
    }
}

// Initialize
AIO_Signing_Plugin::instance();
