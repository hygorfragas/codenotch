<?php

// SPECSFY: US-001 FR-003 AC-011

it('nao registra smartphone antes do limite', function () {
    $response = $this->postJson('/snitch/episodes/smartphone', [
        'employee_id' => 1,
        'enabled' => true,
        'limit_exceeded' => false,
    ]);

    $response->assertNoContent();
});
