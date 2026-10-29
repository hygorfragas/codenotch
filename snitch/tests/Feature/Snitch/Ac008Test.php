<?php

// SPECSFY: US-001 FR-002 AC-008

it('nao cria registro de ociosidade fora da zona de passagem', function () {
    $response = $this->postJson('/snitch/episodes/idle-zone', [
        'employee_id' => 1,
        'zone' => 'descanso',
        'zone_type' => 'descanso',
    ]);

    $response->assertNoContent();
});
