<?php

// SPECSFY: US-001 FR-003 AC-010

it('nao conta ociosidade de smartphone desligado', function () {
    $response = $this->postJson('/snitch/episodes/smartphone', [
        'employee_id' => 1,
        'enabled' => false,
    ]);

    $response->assertNoContent();
});
