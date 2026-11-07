<?php

namespace Tests;

use App\Models\Company;
use Database\Seeders\SnitchDemoSeeder;

abstract class SnitchFeatureTestCase extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();

        $this->withoutVite();

        if (Company::query()->count() === 0) {
            $this->seed(SnitchDemoSeeder::class);
        }

        if (\App\Models\Camera::query()->count() === 0) {
            \App\Models\Camera::query()->create([
                'location_id' => 1,
                'name' => 'Camera Teste',
                'sector' => 'Acesso',
                'stream_url' => 'rtsp://example.test/stream',
                'credential' => 'secret-not-in-ui',
            ]);
        }
    }
}
