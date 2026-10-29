<?php

namespace App\Providers;

use App\Contracts\VisionEngine;
use App\Services\HttpVisionEngine;
use Illuminate\Support\ServiceProvider;

class SnitchServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->mergeConfigFrom(config_path('snitch.php'), 'snitch');

        $this->app->singleton(VisionEngine::class, HttpVisionEngine::class);
    }

    public function boot(): void
    {
        //
    }
}
