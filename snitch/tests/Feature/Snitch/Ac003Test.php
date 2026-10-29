<?php

// SPECSFY: US-001 FR-003 AC-003

it('conta minuto de smartphone depois do limite', function () {
    $response = $this->postJson('/snitch/episodes/smartphone', ['employee_id' => 1, 'enabled' => true]);
    $response->assertCreated();
});
