<?php

// SPECSFY: US-001 FR-001 AC-007

it('nao liga registro a funcionario sem vinculo', function () {
    $response = $this->postJson('/snitch/episodes/missing-ppe', ['employee_id' => null]);
    $response->assertAccepted();
});
