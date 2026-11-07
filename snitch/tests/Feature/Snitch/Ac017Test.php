<?php

// SPECSFY: NFR-001 AC-017

it('processa fluxo com motor python colocado na mesma vps', function () {
    expect(config('snitch.deployment.colocated'))->toBeTrue()
        ->and(config('snitch.vision.engine_url'))->toContain('127.0.0.1');
});
