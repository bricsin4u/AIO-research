<?php
/**
 * Plugin Name: AIO Protocol Support (Auto-Sync)
 * Description: Automatically adds AI Optimization (AIO) support. Zero config - syncs with your posts instantly.
 * Version: 2.0
 * Author: AIFUSION Research
 */

if (!defined('ABSPATH')) exit;

class AIO_WordPress_Plugin {
    
    public function __construct() {
        // Discovery signals
        add_action('wp_head', [$this, 'add_head_tags']);
        add_filter('robots_txt', [$this, 'add_robots_directives'], 10, 2);
        
        // Dynamic Endpoints
        add_action('init', [$this, 'add_endpoints']);
        add_action('template_redirect', [$this, 'handle_endpoints']);
    }
    
    public function add_head_tags() {
        echo '<link rel="alternate" type="application/aio+json" href="' . site_url('/ai-content.aio') . '" />' . "\n";
    }
    
    public function add_robots_directives($output, $public) {
        $output .= "\n# AIO Discovery\n";
        $output .= "AIO-Manifest: " . site_url('/ai-manifest.json') . "\n";
        $output .= "AIO-Content: " . site_url('/ai-content.aio') . "\n";
        $output .= "AIO-Version: 2.1\n";
        return $output;
    }
    
    public function add_endpoints() {
        add_rewrite_rule('^ai-content\.aio/?', 'index.php?aio_content=1', 'top');
        add_rewrite_rule('^ai-manifest\.json/?', 'index.php?aio_manifest=1', 'top');
        add_rewrite_tag('%aio_content%', '([^&]+)');
        add_rewrite_tag('%aio_manifest%', '([^&]+)');
    }
    
    public function handle_endpoints() {
        global $wp_query;
        if ($wp_query->get('aio_manifest')) {
            $this->serve_manifest();
            exit;
        }
        if ($wp_query->get('aio_content')) {
            $this->serve_content_dynamic();
            exit;
        }
    }
    
    private function serve_manifest() {
        // Dynamic count of published posts
        $count = wp_count_posts()->publish;
        
        $manifest = [
            '$schema' => 'https://aio-standard.org/schema/v2.1/manifest.json',
            'aio_version' => '2.1',
            'site' => [
                'name' => get_bloginfo('name'),
                'domain' => parse_url(site_url(), PHP_URL_HOST)
            ],
            'content' => [
                'primary' => '/ai-content.aio',
                'chunks_count' => (int)$count,
                'update_frequency' => 'realtime'
            ]
        ];
        wp_send_json($manifest);
    }
    
    private function serve_content_dynamic() {
        // 1. Fetch latest 50 posts (auto-sync with DB)
        // For production, this should support pagination or ?since= parameter
        $query = new WP_Query([
            'post_type' => 'post',
            'post_status' => 'publish',
            'posts_per_page' => 50,
            'orderby' => 'modified', // Get latest modified content
            'order' => 'DESC'
        ]);
        
        $chunks = [];
        $index = [];
        
        if ($query->have_posts()) {
            while ($query->have_posts()) {
                $query->the_post();
                
                // 2. Auto-Extract Content
                // We use WordPress built-in functions to get clean content
                $content = get_the_content();
                
                // Strip shorcodes and tags
                $clean_text = strip_shortcodes($content);
                $clean_text = wp_strip_all_tags($clean_text);
                
                // Reformat as markdown-ish
                $title = get_the_title();
                $clean_text = "# $title\n\n" . $clean_text;
                
                $id = 'post-' . get_the_ID();
                $tokens = ceil(strlen($clean_text) / 4);
                
                // 3. Build Chunk
                $index[] = [
                    'id' => $id,
                    'path' => parse_url(get_permalink(), PHP_URL_PATH),
                    'title' => $title,
                    'modified' => get_the_modified_date('c'), // Critical for detailed syncing
                    'token_estimate' => $tokens
                ];
                
                $chunks[] = [
                    'id' => $id,
                    'format' => 'markdown',
                    'content' => $clean_text,
                    'hash' => 'sha256:' . hash('sha256', $clean_text)
                ];
            }
        }
        
        $data = [
            '$schema' => 'https://aio-standard.org/schema/v2.1/content.json',
            'aio_version' => '2.1',
            'generated' => date('c'),
            'index' => $index,
            'content' => $chunks
        ];
        
        // Cache for 5 minutes to reduce DB load, but essentially real-time
        header('Cache-Control: max-age=300');
        wp_send_json($data);
    }
}

new AIO_WordPress_Plugin();
