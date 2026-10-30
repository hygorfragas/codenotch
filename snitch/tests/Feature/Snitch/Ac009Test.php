<?php

// SPECSFY: US-001 FR-002 AC-009

it('nao registra ociosidade sem tempo maximo na zona de passagem', function () {
    $response = $this->postJson('/snitch/episodes/idle-zone', [
        'employee_id' => 1,
        'zone' => 'passagem',
        'zone_type' => 'passagem',
    ]);

    $response->assertNoContent();
});
