<?php

// SPECSFY: US-002 FR-004 AC-012

it('mostra erro quando o SSE para', function () {
    $response = $this->getJson('/snitch/cameras/1/live?sse=down');
    $response->assertStatus(503);
});
