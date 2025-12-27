<?php
/**
 * AIO Signing for Laravel
 * 
 * Installation:
 * 1. Copy this file to app/Providers/AIOServiceProvider.php
 * 2. Copy AIOMiddleware.php to app/Http/Middleware/
 * 3. Add to config/app.php providers: App\Providers\AIOServiceProvider::class
 * 4. Add to .env: AIO_PRIVATE_KEY=xxx, AIO_PUBLIC_KEY=xxx
 * 5. Add middleware to routes or kernel
 * 
 * Usage in Blade:
 *   @aioHead($markdown)
 *   @aioShadow($markdown)
 */

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Blade;

class AIOServiceProvider extends ServiceProvider
{
    public function register()
    {
        $this->app->singleton('aio', function ($app) {
            return new \App\Services\AIOSigning(
                config('services.aio.private_key', env('AIO_PRIVATE_KEY')),
                config('services.aio.public_key', env('AIO_PUBLIC_KEY'))
            );
        });
    }

    public function boot()
    {
        // Blade directive for meta tags
        Blade::directive('aioHead', function ($expression) {
            return "<?php echo app('aio')->renderMetaTags($expression); ?>";
        });

        // Blade directive for markdown shadow
        Blade::directive('aioShadow', function ($expression) {
            return "<?php echo app('aio')->renderShadow($expression); ?>";
        });

        // Publish config
        $this->publishes([
            __DIR__ . '/../../config/aio.php' => config_path('aio.php'),
        ], 'aio-config');
    }
}
