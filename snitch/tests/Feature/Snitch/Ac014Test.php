<?php

// SPECSFY: US-001 FR-005 AC-014

it('aviso fica so no painel sem canal extra', function () {
    $response = $this->postJson('/snitch/alerts', ['channels' => []]);
    $response->assertCreated();
});
