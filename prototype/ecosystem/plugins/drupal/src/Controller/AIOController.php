<?php

namespace Drupal\aio\Controller;

use Drupal\Core\Controller\ControllerBase;
use Symfony\Component\HttpFoundation\JsonResponse;

class AIOController extends ControllerBase {

  public function manifest() {
    $config = \Drupal::config('system.site');
    
    // Count published nodes
    $query = \Drupal::entityQuery('node')
      ->condition('status', 1)
      ->accessCheck(TRUE);
    $count = $query->count()->execute();

    $data = [
      '$schema' => 'https://aio-standard.org/schema/v2.1/manifest.json',
      'aio_version' => '2.1',
      'site' => [
        'name' => $config->get('name'),
        'domain' => \Drupal::request()->getHost(),
      ],
      'content' => [
        'primary' => '/ai-content.aio',
        'chunks_count' => (int)$count,
        'update_frequency' => 'realtime',
      ],
    ];

    return new JsonResponse($data);
  }

  public function content() {
    // Fetch latest 50 nodes
    $query = \Drupal::entityQuery('node')
      ->condition('status', 1)
      ->sort('changed', 'DESC')
      ->range(0, 50)
      ->accessCheck(TRUE); // Check permissions
      
    $nids = $query->execute();
    $nodes = \Drupal::entityTypeManager()->getStorage('node')->loadMultiple($nids);

    $chunks = [];
    $index = [];

    foreach ($nodes as $node) {
      $processed = _aio_process_node($node);
      
      $index[] = [
        'id' => $processed['id'],
        'path' => $processed['path'],
        'title' => $processed['title'],
        'modified' => $processed['modified'],
        'token_estimate' => $processed['token_estimate'],
      ];
      
      $chunks[] = [
        'id' => $processed['id'],
        'format' => 'markdown',
        'content' => $processed['content'],
        'hash' => 'sha256:' . hash('sha256', $processed['content']),
      ];
    }

    $data = [
      '$schema' => 'https://aio-standard.org/schema/v2.1/content.json',
      'aio_version' => '2.1',
      'generated' => date('c'),
      'index' => $index,
      'content' => $chunks,
    ];

    // Cache tagging for invalidation
    $response = new JsonResponse($data);
    $cache_metadata = new \Drupal\Core\Cache\CacheableMetadata();
    $cache_metadata->addCacheTags(['node_list']);
    $response->addCacheableDependency($cache_metadata);

    return $response;
  }
}
