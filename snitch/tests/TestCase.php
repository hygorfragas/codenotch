<?php

namespace Tests;

use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Illuminate\Support\Facades\Artisan;
use Tests\Support\SnitchTestSeeder;

abstract class TestCase extends BaseTestCase
{
    private static bool $snitchSchemaReady = false;

    protected function setUp(): void
    {
        parent::setUp();

        if (! self::$snitchSchemaReady) {
            Artisan::call('migrate', ['--force' => true]);
            SnitchTestSeeder::seed();
            self::$snitchSchemaReady = true;
        }
    }
}
