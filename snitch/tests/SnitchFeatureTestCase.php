<?php

namespace Tests;

use App\Models\Company;
use Database\Seeders\SnitchDemoSeeder;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;

abstract class SnitchFeatureTestCase extends BaseTestCase
{
    protected function setUp(): void
    {
        parent::setUp();

        if (Company::query()->count() === 0) {
            $this->seed(SnitchDemoSeeder::class);
        }
    }
}
