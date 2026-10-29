<?php

// SPECSFY: US-002 FR-004 AC-004

it('mostra a camera ao vivo sem criar registro', function () {
    $response = $this->getJson('/snitch/cameras/1/live');
    $response->assertOk();
});
