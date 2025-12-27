<?php
/**
 * AIO Signing Library for PHP
 * 
 * Works with WordPress, Laravel, Symfony, vanilla PHP, etc.
 * 
 * Requirements: PHP 7.4+ with sodium extension (included by default in PHP 7.2+)
 * 
 * Usage:
 *   require_once 'aio-signing.php';
 *   
 *   // Generate keys (once, save these!)
 *   $keys = AIO::generateKeys();
 *   
 *   // Sign and inject into HTML
 *   $html = AIO::injectAIOLayer($html, $markdown, $keys['private'], $keys['public']);
 */

class AIO {
    
    /**
     * Generate a new Ed25519 keypair
     */
    public static function generateKeys(): array {
        $keyPair = sodium_crypto_sign_keypair();
        
        return [
            'public' => base64_encode(sodium_crypto_sign_publickey($keyPair)),
            'private' => base64_encode(sodium_crypto_sign_secretkey($keyPair)),
            'algorithm' => 'Ed25519'
        ];
    }
    
    /**
     * Hash content using SHA-256
     */
    public static function hashContent(string $content): string {
        return hash('sha256', trim($content));
    }
    
    /**
     * Sign markdown content
     */
    public static function signMarkdown(string $markdown, string $privateKeyB64): array {
        $timestamp = gmdate('Y-m-d\TH:i:s\Z');
        $contentHash = self::hashContent($markdown);
        
        $payload = json_encode([
            'content_hash' => $contentHash,
            'timestamp' => $timestamp,
            'algorithm' => 'Ed25519'
        ], JSON_UNESCAPED_SLASHES);
        
        $privateKey = base64_decode($privateKeyB64);
        $signature = sodium_crypto_sign_detached($payload, $privateKey);
        
        return [
            'signature' => base64_encode($signature),
            'content_hash' => $contentHash,
            'timestamp' => $timestamp,
            'algorithm' => 'Ed25519'
        ];
    }
    
    /**
     * Verify a signature
     */
    public static function verifySignature(
        string $markdown, 
        string $signatureB64, 
        string $timestamp, 
        string $publicKeyB64
    ): bool {
        $contentHash = self::hashContent($markdown);
        
        $payload = json_encode([
            'content_hash' => $contentHash,
            'timestamp' => $timestamp,
            'algorithm' => 'Ed25519'
        ], JSON_UNESCAPED_SLASHES);
        
        $signature = base64_decode($signatureB64);
        $publicKey = base64_decode($publicKeyB64);
        
        return sodium_crypto_sign_verify_detached($signature, $payload, $publicKey);
    }
    
    /**
     * Generate AIO meta tags
     */
    public static function generateMetaTags(array $signResult, string $publicKey = ''): string {
        return <<<HTML
    <meta name="aio-truth-signature" content="{$signResult['signature']}">
    <meta name="aio-content-hash" content="{$signResult['content_hash']}">
    <meta name="aio-public-key" content="{$publicKey}">
    <meta name="aio-last-verified" content="{$signResult['timestamp']}">
    <meta name="aio-signature-algorithm" content="{$signResult['algorithm']}">
HTML;
    }
    
    /**
     * Generate markdown shadow block
     */
    public static function generateMarkdownShadow(string $markdown): string {
        $escaped = htmlspecialchars($markdown, ENT_NOQUOTES, 'UTF-8');
        return <<<HTML
    <section class="ai-only" aria-hidden="true" style="display:none!important">
        <script type="text/markdown" id="aio-narrative-content">
{$markdown}
        </script>
    </section>
HTML;
    }
    
    /**
     * Inject AIO layer into HTML
     */
    public static function injectAIOLayer(
        string $html, 
        string $markdown, 
        string $privateKey, 
        string $publicKey
    ): string {
        $signResult = self::signMarkdown($markdown, $privateKey);
        $metaTags = self::generateMetaTags($signResult, $publicKey);
        $shadow = self::generateMarkdownShadow($markdown);
        
        // Inject meta tags before </head>
        $html = str_replace('</head>', $metaTags . "\n</head>", $html);
        
        // Inject shadow before </body>
        $html = str_replace('</body>', $shadow . "\n</body>", $html);
        
        return $html;
    }
    
    /**
     * WordPress filter hook helper
     * 
     * Usage in functions.php:
     *   add_filter('the_content', [AIO::class, 'wordpressFilter']);
     */
    public static function wordpressFilter(string $content): string {
        // Get keys from wp_options or constants
        $privateKey = defined('AIO_PRIVATE_KEY') ? AIO_PRIVATE_KEY : get_option('aio_private_key');
        $publicKey = defined('AIO_PUBLIC_KEY') ? AIO_PUBLIC_KEY : get_option('aio_public_key');
        
        if (!$privateKey || !$publicKey) {
            return $content;
        }
        
        // Generate markdown from content (strip HTML)
        $markdown = self::htmlToMarkdown($content);
        
        // Sign it
        $signResult = self::signMarkdown($markdown, $privateKey);
        
        // Append shadow to content
        $shadow = self::generateMarkdownShadow($markdown);
        
        return $content . $shadow;
    }
    
    /**
     * Simple HTML to Markdown conversion with AIO improvements
     */
    public static function htmlToMarkdown(string $html): string {
        // 1. Extract Metadata & Citations
        $metadata = [];
        $citations = [];
        
        // Title
        if (preg_match('/<title[^>]*>(.*?)<\/title>/i', $html, $matches)) {
            $metadata['title'] = trim($matches[1]);
        }
        
        // Site Name (OG or H1)
        if (preg_match('/<meta[^>]*property=["\']og:site_name["\'][^>]*content=["\']([^"\']*)["\']/i', $html, $matches)) {
            $metadata['site_name'] = $matches[1];
        } elseif (preg_match('/<h1[^>]*>(.*?)<\/h1>/i', $html, $matches)) {
            // Fallback to first H1
             $metadata['site_name'] = strip_tags($matches[1]);
        }
        
        // Author
        if (preg_match('/<meta[^>]*name=["\']author["\'][^>]*content=["\']([^"\']*)["\']/i', $html, $matches)) {
            $metadata['author'] = $matches[1];
        } elseif (preg_match('/By\s+([^|<]+)/i', $html, $matches)) {
             // Simple heuristic for "By [Name]"
             $metadata['author'] = trim($matches[1]);
        }
        
        // Date
        if (preg_match('/<meta[^>]*property=["\']article:published_time["\'][^>]*content=["\']([^"\']*)["\']/i', $html, $matches)) {
            $metadata['date'] = $matches[1];
        }
        
        // URL
        if (preg_match('/<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']*)["\']/i', $html, $matches)) {
            $metadata['url'] = $matches[1];
        } elseif (preg_match('/<meta[^>]*property=["\']og:url["\'][^>]*content=["\']([^"\']*)["\']/i', $html, $matches)) {
            $metadata['url'] = $matches[1];
        }
        
        // Citations (External Links)
        if (preg_match_all('/<a[^>]*href=["\'](http[^"\']*)["\'][^>]*>/i', $html, $matches)) {
            foreach ($matches[1] as $href) {
                if (strpos($href, 'localhost') === false && strpos($href, '127.0.0.1') === false) {
                    if (!in_array($href, $citations)) {
                        $citations[] = $href;
                    }
                }
            }
        }
        if (!empty($citations)) {
            $metadata['citations'] = $citations;
        }

        // 2. Build Frontmatter
        $frontmatter = "---\n";
        foreach ($metadata as $key => $value) {
            if ($key === 'citations') {
                $frontmatter .= "citations:\n";
                foreach ($value as $cite) {
                    $frontmatter .= "  - $cite\n";
                }
            } else {
                $safe_value = str_replace('"', '\\"', $value);
                $frontmatter .= "$key: \"$safe_value\"\n";
            }
        }
        $frontmatter .= "---\n\n";

        // 3. Clean Noise
        // Remove scripts, styles, nav, footer, ads
        $html = preg_replace('/<(script|style|nav|footer)[^>]*>.*?<\/\1>/is', '', $html);
        $html = preg_replace('/<div[^>]*class=["\'][^"\']*(ad-|banner|promo|sidebar)[^"\']*["\'][^>]*>.*?<\/div>/is', '', $html);

        // 4. Isolate Main Content (Heuristic)
        // Try to find <main> or <article> to narrow down the content
        if (preg_match('/<main[^>]*>(.*?)<\/main>/is', $html, $matches)) {
            $html = $matches[1];
        } elseif (preg_match('/<article[^>]*>(.*?)<\/article>/is', $html, $matches)) {
            $html = $matches[1];
        }

        // 5. Convert Body
        // Basic conversion - for production use league/html-to-markdown
        $md = strip_tags($html, '<h1><h2><h3><h4><p><ul><ol><li><strong><em><a>');
        
        // Headers
        $md = preg_replace('/<h1[^>]*>(.*?)<\/h1>/i', "# $1\n\n", $md);
        $md = preg_replace('/<h2[^>]*>(.*?)<\/h2>/i', "## $1\n\n", $md);
        $md = preg_replace('/<h3[^>]*>(.*?)<\/h3>/i', "### $1\n\n", $md);
        
        // Paragraphs
        $md = preg_replace('/<p[^>]*>(.*?)<\/p>/is', "$1\n\n", $md);
        
        // Bold/Italic
        $md = preg_replace('/<strong[^>]*>(.*?)<\/strong>/i', "**$1**", $md);
        $md = preg_replace('/<em[^>]*>(.*?)<\/em>/i', "*$1*", $md);
        
        // Links
        $md = preg_replace('/<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)<\/a>/i', "[$2]($1)", $md);
        
        // Lists
        $md = preg_replace('/<li[^>]*>(.*?)<\/li>/i', "- $1\n", $md);
        $md = preg_replace('/<\/?[uo]l[^>]*>/i', "\n", $md);
        
        // Clean up
        $md = strip_tags($md);
        $md = preg_replace('/\n{3,}/', "\n\n", $md);
        
        return $frontmatter . trim($md);
    }
    
    /**
     * Laravel middleware helper
     * 
     * Usage:
     *   Route::middleware([AIO::laravelMiddleware()])->group(...)
     */
    public static function laravelMiddleware(): \Closure {
        return function ($request, $next) {
            $response = $next($request);
            
            $content = $response->getContent();
            
            if (strpos($content, '</html>') !== false) {
                $privateKey = config('aio.private_key') ?? env('AIO_PRIVATE_KEY');
                $publicKey = config('aio.public_key') ?? env('AIO_PUBLIC_KEY');
                
                if ($privateKey && $publicKey) {
                    // Get markdown from view data or generate from content
                    $markdown = $request->attributes->get('aio_markdown') 
                        ?? self::htmlToMarkdown(strip_tags($content));
                    
                    $content = self::injectAIOLayer($content, $markdown, $privateKey, $publicKey);
                    $response->setContent($content);
                }
            }
            
            return $response;
        };
    }
}

// CLI helper for key generation
if (php_sapi_name() === 'cli' && isset($argv[1]) && $argv[1] === 'generate-keys') {
    $keys = AIO::generateKeys();
    echo "Generated AIO Keys:\n";
    echo "Public Key:  {$keys['public']}\n";
    echo "Private Key: {$keys['private']}\n";
    echo "\nAdd to your .env or wp-config.php:\n";
    echo "AIO_PUBLIC_KEY={$keys['public']}\n";
    echo "AIO_PRIVATE_KEY={$keys['private']}\n";
}
