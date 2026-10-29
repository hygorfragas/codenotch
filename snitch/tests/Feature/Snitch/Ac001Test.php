<?php

// SPECSFY: US-001 FR-001 AC-001

it('guarda foto, data e hora quando falta um EPI obrigatório', function () {
    $response = $this->postJson('/snitch/episodes/missing-ppe', [
        'employee_id' => 1,
        'location_id' => 1,
        'required_ppe' => 'capacete',
        'detected_ppe' => [],
    ]);

    $response->assertCreated();
    $response->assertJsonStructure([
        'photo',
        'recorded_at',
    ]);
});
