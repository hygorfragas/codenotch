<?php

// SPECSFY: US-001 FR-005 AC-005

it('avisa no painel quando o registro nasce', function () {
    $response = $this->postJson('/snitch/alerts', ['type' => 'epi']);
    $response->assertCreated();
});
