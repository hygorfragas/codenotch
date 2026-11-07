<?php

use App\Enums\EpisodeType;
use App\Models\Company;
use App\Models\Episode;
use App\Models\Location;
use Illuminate\Support\Carbon;

// SPECSFY: NFR-001 AC-016

it('mantem registros isolados por empresa no postgres da vps', function () {
    $otherCompany = Company::query()->create(['name' => 'Empresa Sul']);
    $otherLocation = Location::query()->create([
        'company_id' => $otherCompany->id,
        'name' => 'Patio Sul',
    ]);

    Episode::query()->create([
        'company_id' => 1,
        'location_id' => 1,
        'employee_id' => 1,
        'type' => EpisodeType::MissingPpe,
        'photo' => 'snitch/episodes/missing_ppe/test-a.jpg',
        'recorded_at' => Carbon::now(),
        'metadata' => [],
    ]);

    Episode::query()->create([
        'company_id' => $otherCompany->id,
        'location_id' => $otherLocation->id,
        'employee_id' => null,
        'type' => EpisodeType::IdleZone,
        'photo' => 'snitch/episodes/idle_zone/test-b.jpg',
        'recorded_at' => Carbon::now(),
        'metadata' => [],
    ]);

    $companyOneCount = Episode::query()->where('company_id', 1)->count();
    $otherCount = Episode::query()->where('company_id', $otherCompany->id)->count();

    expect($companyOneCount)->toBeGreaterThan(0)
        ->and($otherCount)->toBe(1)
        ->and(Episode::query()->where('company_id', $otherCompany->id)->sole()->location_id)->toBe($otherLocation->id);
});
