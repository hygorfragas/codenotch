<?php

use App\Models\Camera;
use App\Models\LocationSmartphoneSetting;

it('entrega o limite de celular configurado para o motor', function () {
    $camera = Camera::query()->first();
    LocationSmartphoneSetting::query()->updateOrCreate(
        ['location_id' => $camera->location_id],
        ['enabled' => true, 'hand_limit_seconds' => 15],
    );

    $this->getJson('/snitch/cameras/'.$camera->id.'/engine-config')
        ->assertOk()
        ->assertJsonPath('smartphone.enabled', true)
        ->assertJsonPath('smartphone.hand_limit_seconds', 15)
        ->assertJsonPath('smartphone.max_continuous_seconds', 15);
});
