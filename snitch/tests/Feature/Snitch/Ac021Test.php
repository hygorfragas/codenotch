<?php

use App\Models\Camera;

// SPECSFY: NFR-002 AC-021

it('nao mostra credencial do dvr no historico do funcionario', function () {
    Camera::query()->firstOrFail()->update([
        'dvr_url' => 'rtsp://usuario-secreto:senha@dvr.local/stream',
    ]);

    $response = $this->get('/snitch/employees/1');

    $response->assertOk();
    $response->assertDontSee('usuario-secreto', false);
    $response->assertDontSee('senha@dvr', false);
});
