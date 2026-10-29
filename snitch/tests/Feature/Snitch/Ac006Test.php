<?php

// SPECSFY: US-001 FR-001 AC-006

it('nao registra EPI que nao foi marcado', function () {
    $response = $this->postJson('/snitch/episodes/missing-ppe', ['required' => false]);
    $response->assertNoContent();
});
