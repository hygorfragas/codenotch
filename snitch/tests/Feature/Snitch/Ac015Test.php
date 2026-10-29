<?php

// SPECSFY: US-001 FR-005 AC-015

it('nao envia EPI em canal so de ociosidade', function () {
    $response = $this->postJson('/snitch/alerts', ['type' => 'epi', 'channel' => 'whatsapp-idle']);
    $response->assertCreated();
});
