<?php

use App\Models\Camera;
use App\Models\Company;
use App\Models\Episode;
use App\Models\Zone;

it('grava permanencia e zona restrita sem apagar o epi ausente', function () {
    $companyId = Company::query()->orderBy('id')->value('id');
    $camera = Camera::query()->whereHas('location', fn ($query) => $query->where('company_id', $companyId))->first()
        ?? Camera::query()->first();
    $passage = Zone::query()->create([
        'camera_id' => $camera->id,
        'name' => 'Banheiro',
        'type' => 'passagem',
        'max_dwell_seconds' => 40,
        'polygon' => [[0, 0], [20, 0], [20, 20]],
    ]);
    $restricted = Zone::query()->create([
        'camera_id' => $camera->id,
        'name' => 'Área restrita',
        'type' => 'restrita',
        'polygon' => [[0, 0], [10, 0], [10, 10]],
    ]);

    $this->postJson('/snitch/episodes/ppe', [
        'employee_id' => null,
        'location_id' => $camera->location_id,
        'camera_id' => $camera->id,
        'required_ppe' => ['helmet', 'gloves', 'vest'],
        'detected_ppe' => ['boots'],
        'missing_ppe' => ['helmet', 'gloves', 'vest'],
        'missing_items' => ['helmet', 'gloves', 'vest'],
        'missing_ppe_labels_pt' => ['Capacete', 'Luvas', 'Colete refletivo'],
        'photo' => 'data:image/jpeg;base64,abc',
    ])->assertAccepted();

    $this->postJson('/snitch/episodes/idle-zone', [
        'location_id' => $camera->location_id,
        'camera_id' => $camera->id,
        'zone_id' => $passage->id,
        'zone' => 'Banheiro',
        'zone_type' => 'passagem',
        'max_time_seconds' => 40,
        'time_exceeded' => true,
        'dwell_seconds' => 41,
        'tracker_id' => 9,
        'photo' => 'data:image/jpeg;base64,abc',
    ])->assertCreated();

    $this->postJson('/snitch/episodes/idle-zone', [
        'location_id' => $camera->location_id,
        'camera_id' => $camera->id,
        'zone_id' => $restricted->id,
        'zone' => 'Área restrita',
        'zone_type' => 'restrita',
        'time_exceeded' => true,
        'dwell_seconds' => 2,
        'tracker_id' => 9,
        'photo' => 'data:image/jpeg;base64,abc',
    ])->assertCreated();

    $types = Episode::query()->latest('id')->limit(3)->get();
    expect($types->pluck('type')->map->value->all())->toContain('missing_ppe', 'idle_zone');

    $passageEpisode = Episode::query()->where('zone_id', $passage->id)->latest('id')->first();
    expect($passageEpisode->camera_id)->toBe($camera->id);
    expect($passageEpisode->episodeSummary())->toBe('Permanência em zona: Banheiro (41s / 40s)');

    $restrictedEpisode = Episode::query()->where('zone_id', $restricted->id)->latest('id')->first();
    expect($restrictedEpisode->typeLabel())->toBe('Zona restrita');
    expect($restrictedEpisode->episodeSummary())->toBe('Zona restrita: Área restrita (2s)');

    $ppeEpisode = Episode::query()->where('type', 'missing_ppe')->latest('id')->first();
    expect($ppeEpisode->metadata['missing_ppe'])->toBe(['helmet', 'gloves', 'vest']);
    expect($ppeEpisode->episodeSummary())->toBe('EPI ausente: Capacete, Luvas, Colete refletivo');

    $this->get('/snitch/company/dashboard')
        ->assertOk()
        ->assertSee('Permanência em zona: Banheiro (41s / 40s)', false)
        ->assertSee('Zona restrita: Área restrita (2s)', false)
        ->assertSee('EPI ausente: Capacete, Luvas, Colete refletivo', false);

    $this->get('/snitch/locations/'.$camera->location_id)
        ->assertOk()
        ->assertSee('Permanência em zona: Banheiro (41s / 40s)', false)
        ->assertSee('Zona restrita: Área restrita (2s)', false)
        ->assertSee('EPI ausente: Capacete, Luvas, Colete refletivo', false);

    $this->get('/snitch/cameras/'.$camera->id.'/live/painel')
        ->assertOk()
        ->assertSee('id="live-zones"', false)
        ->assertSee('Permanência em zona', false)
        ->assertSee('Zona restrita', false)
        ->assertSee('EPI ausente:', false)
        ->assertSee('EPI obrigatório faltando: sim', false);
});
