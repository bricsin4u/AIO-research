<?php
/**
 * AIO Middleware for Laravel
 * 
 * Copy to: app/Http/Middleware/AIOMiddleware.php
 * 
 * Register in app/Http/Kernel.php:
 *   protected $middlewareAliases = [
 *       'aio' => \App\Http\Middleware\AIOMiddleware::class,
 *   ];
 * 
 * Usage in routes:
 *   Route::get('/article/{slug}', [ArticleController::class, 'show'])->middleware('aio');
 */

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class AIOMiddleware
{
    public function handle(Request $request, Closure $next): Response
    {
        $response = $next($request);

        // Only process HTML responses
        $contentType = $response->headers->get('Content-Type', '');
        if (!str_contains($contentType, 'text/html') && !empty($contentType)) {
            return $response;
        }

        $content = $response->getContent();
        
        // Check if it's HTML
        if (!str_contains($content, '</html>')) {
            return $response;
        }

        // Get markdown from request attribute (set by controller)
        $markdown = $request->attributes->get('aio_markdown');
        
        if (!$markdown) {
            // Pass full content to allow metadata extraction
            $markdown = app('aio')->htmlToMarkdown($content);
        }

        if ($markdown) {
            $aio = app('aio');
            $signResult = $aio->sign($markdown);

            if ($signResult) {
                // Inject meta tags
                $metaTags = $aio->renderMetaTags($markdown);
                $content = str_replace('</head>', $metaTags . "\n</head>", $content);

                // Inject shadow
                $shadow = $aio->renderShadow($markdown);
                $content = str_replace('</body>', $shadow . "\n</body>", $content);

                $response->setContent($content);
            }
        }

        return $response;
    }
}
