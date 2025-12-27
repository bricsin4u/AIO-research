<?php
/**
 * AIO Signing Service for Laravel
 * 
 * Copy to: app/Services/AIOSigning.php
 */

namespace App\Services;

class AIOSigning
{
    private string $privateKey;
    private string $publicKey;

    public function __construct(?string $privateKey = null, ?string $publicKey = null)
    {
        $this->privateKey = $privateKey ?? '';
        $this->publicKey = $publicKey ?? '';
    }

    /**
     * Generate new keypair
     */
    public static function generateKeys(): array
    {
        $keypair = sodium_crypto_sign_keypair();
        
        return [
            'private_key' => base64_encode(sodium_crypto_sign_secretkey($keypair)),
            'public_key' => base64_encode(sodium_crypto_sign_publickey($keypair)),
        ];
    }

    /**
     * Hash content
     */
    public function hash(string $content): string
    {
        return hash('sha256', trim($content));
    }

    /**
     * Sign markdown content
     */
    public function sign(string $markdown): ?array
    {
        if (empty($this->privateKey)) {
            return null;
        }

        $timestamp = now()->toIso8601ZuluString();
        $contentHash = $this->hash($markdown);

        $payload = json_encode([
            'content_hash' => $contentHash,
            'timestamp' => $timestamp,
            'algorithm' => 'Ed25519',
        ], JSON_UNESCAPED_SLASHES);

        try {
            $key = base64_decode($this->privateKey);
            $signature = sodium_crypto_sign_detached($payload, $key);

            return [
                'signature' => base64_encode($signature),
                'content_hash' => $contentHash,
                'timestamp' => $timestamp,
                'public_key' => $this->publicKey,
            ];
        } catch (\Exception $e) {
            report($e);
            return null;
        }
    }

    /**
     * Verify signature
     */
    public function verify(string $markdown, string $signature, string $timestamp, ?string $publicKey = null): bool
    {
        $pubKey = $publicKey ?? $this->publicKey;
        $contentHash = $this->hash($markdown);

        $payload = json_encode([
            'content_hash' => $contentHash,
            'timestamp' => $timestamp,
            'algorithm' => 'Ed25519',
        ], JSON_UNESCAPED_SLASHES);

        try {
            $sig = base64_decode($signature);
            $key = base64_decode($pubKey);
            return sodium_crypto_sign_verify_detached($sig, $payload, $key);
        } catch (\Exception $e) {
            return false;
        }
    }

    /**
     * Render meta tags HTML
     */
    public function renderMetaTags(string $markdown): string
    {
        $result = $this->sign($markdown);
        
        if (!$result) {
            return '<!-- AIO: signing failed -->';
        }

        return <<<HTML
<meta name="aio-truth-signature" content="{$result['signature']}">
<meta name="aio-content-hash" content="{$result['content_hash']}">
<meta name="aio-public-key" content="{$result['public_key']}">
<meta name="aio-last-verified" content="{$result['timestamp']}">
<meta name="aio-signature-algorithm" content="Ed25519">
HTML;
    }

    /**
     * Render markdown shadow HTML
     */
    public function renderShadow(string $markdown): string
    {
        $escaped = e($markdown);
        
        return <<<HTML
<section class="ai-only" aria-hidden="true" style="display:none!important">
<script type="text/markdown" id="aio-narrative-content">
{$markdown}
</script>
</section>
HTML;
    }

    /**
     * Convert HTML to Markdown with AIO enhancements
     */
    public function htmlToMarkdown(string $html): string
    {
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
            $metadata['site_name'] = strip_tags($matches[1]);
        }
        
        // Author
        if (preg_match('/<meta[^>]*name=["\']author["\'][^>]*content=["\']([^"\']*)["\']/i', $html, $matches)) {
            $metadata['author'] = $matches[1];
        } elseif (preg_match('/By\s+([^|<]+)/i', $html, $matches)) {
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
        $html = preg_replace('/<(script|style|nav|footer)[^>]*>.*?<\/\1>/is', '', $html);
        $html = preg_replace('/<div[^>]*class=["\'][^"\']*(ad-|banner|promo|sidebar)[^"\']*["\'][^>]*>.*?<\/div>/is', '', $html);

        // 4. Isolate Main Content (Heuristic)
        if (preg_match('/<main[^>]*>(.*?)<\/main>/is', $html, $matches)) {
            $html = $matches[1];
        } elseif (preg_match('/<article[^>]*>(.*?)<\/article>/is', $html, $matches)) {
            $html = $matches[1];
        }

        // 5. Convert Body
        // Strip tags but keep structural elements
        $md = strip_tags($html, '<h1><h2><h3><h4><p><ul><ol><li><strong><em><a>');
        
        // Headers
        $md = preg_replace('/<h1[^>]*>(.*?)<\/h1>/i', "# $1\n\n", $md);
        $md = preg_replace('/<h2[^>]*>(.*?)<\/h2>/i', "## $1\n\n", $md);
        $md = preg_replace('/<h3[^>]*>(.*?)<\/h3>/i', "### $1\n\n", $md);
        
        // Paragraphs
        $md = preg_replace('/<p[^>]*>(.*?)<\/p>/is', "$1\n\n", $md);
        
        // Formatting
        $md = preg_replace('/<strong[^>]*>(.*?)<\/strong>/i', "**$1**", $md);
        $md = preg_replace('/<em[^>]*>(.*?)<\/em>/i', "*$1*", $md);
        $md = preg_replace('/<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)<\/a>/i', "[$2]($1)", $md);
        $md = preg_replace('/<li[^>]*>(.*?)<\/li>/is', "- $1\n", $md);
        $md = preg_replace('/<\/?[uo]l[^>]*>/i', "\n", $md);

        // Clean up
        $md = strip_tags($md);
        $md = preg_replace('/\n{3,}/', "\n\n", $md);
        
        return $frontmatter . trim($md);
    }
}
