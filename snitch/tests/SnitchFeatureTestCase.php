<?php

namespace Tests;

use App\Models\Company;
use Database\Seeders\SnitchDemoSeeder;

abstract class SnitchFeatureTestCase extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();

        if (Company::query()->count() === 0) {
            $this->seed(SnitchDemoSeeder::class);
        }
    }
}
