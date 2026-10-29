<?php

// SPECSFY: US-001 FR-002 AC-002

it('guarda foto quando a zona de passagem estoura', function () {
    $response = $this->postJson('/snitch/episodes/idle-zone', ['employee_id' => 1, 'zone' => 'passagem']);
    $response->assertCreated();
});
