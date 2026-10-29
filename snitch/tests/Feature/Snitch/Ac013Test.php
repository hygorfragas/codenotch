<?php

// SPECSFY: US-002 FR-004 AC-013

it('lista vazia sem camera', function () {
    $response = $this->getJson('/snitch/locations/1/cameras');
    $response->assertOk();
});
