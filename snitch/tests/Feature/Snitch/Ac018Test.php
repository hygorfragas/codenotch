<?php

use App\Enums\EpisodeType;
use App\Models\Company;
use App\Models\Episode;
use App\Models\Location;
use App\Services\DashboardQuery;
use Illuminate\Support\Carbon;

// SPECSFY: NFR-001 AC-018

it('nao expoe registros de outra empresa no painel', function () {
    $dashboard = app(DashboardQuery::class);
    $company = $dashboard->defaultCompany();
    $totalsBefore = $dashboard->episodeTotals($company);

    $otherCompany = Company::query()->create(['name' => 'Empresa Oculta']);
    $otherLocation = Location::query()->create([
        'company_id' => $otherCompany->id,
        'name' => 'Patio oculto',
    ]);

    Episode::query()->create([
        'company_id' => $otherCompany->id,
        'location_id' => $otherLocation->id,
        'employee_id' => null,
        'type' => EpisodeType::Smartphone,
        'photo' => 'snitch/episodes/smartphone/outro.jpg',
        'recorded_at' => Carbon::now(),
        'metadata' => ['marker' => 'EMPRESA_OCULTA_NAO_DEVE_APARECER'],
    ]);

    $totalsAfter = $dashboard->episodeTotals($company);
    $visible = $dashboard->anonymousRecentEpisodes($company);

    expect($totalsAfter)->toBe($totalsBefore)
        ->and($visible->every(fn ($episode) => $episode->company_id === $company->id))->toBeTrue();
});
