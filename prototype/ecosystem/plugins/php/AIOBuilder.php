<?php

/**
 * AIO Generator Class for PHP
 * 
 * Simple, zero-dependency class to generate AIO content.
 * 
 * Usage:
 *   $aio = new AIOBuilder("My Site", "example.com");
 *   $aio->addChunk("home", "# Welcome", "Home page", ["welcome"]);
 *   
 *   header('Content-Type: application/json');
 *   echo $aio->toJson();
 */

class AIOBuilder {
    private $site_name;
    private $domain;
    private $chunks = [];
    
    public function __construct($site_name, $domain) {
        $this->site_name = $site_name;
        $this->domain = $domain;
    }
    
    public function addChunk($id, $content, $title = "", $keywords = []) {
        $this->chunks[] = [
            'id' => $id,
            'content' => $content,
            'title' => $title ?: $id,
            'keywords' => $keywords
        ];
    }
    
    public function toJson() {
        $index = [];
        $content = [];
        
        foreach ($this->chunks as $chunk) {
            $tokens = ceil(strlen($chunk['content']) / 4);
            
            $index[] = [
                'id' => $chunk['id'],
                'path' => '/',
                'title' => $chunk['title'],
                'keywords' => $chunk['keywords'],
                'token_estimate' => $tokens
            ];
            
            $content[] = [
                'id' => $chunk['id'],
                'format' => 'markdown',
                'content' => $chunk['content'],
                'hash' => 'sha256:' . hash('sha256', $chunk['content'])
            ];
        }
        
        $data = [
            '$schema' => 'https://aio-standard.org/schema/v2.1/content.json',
            'aio_version' => '2.1',
            'generated' => date('c'),
            'index' => $index,
            'content' => $content
        ];
        
        return json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    }
    
    public function getManifest() {
        return json_encode([
            '$schema' => 'https://aio-standard.org/schema/v2.1/manifest.json',
            'aio_version' => '2.1',
            'site' => [
                'name' => $this->site_name,
                'domain' => $this->domain
            ],
            'content' => [
                'primary' => '/ai-content.aio',
                'chunks_count' => count($this->chunks)
            ]
        ], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    }
    
    public function printRobotsDirectives() {
        return "AIO-Manifest: /ai-manifest.json\n" .
               "AIO-Content: /ai-content.aio\n" . 
               "AIO-Version: 2.1";
    }
}
