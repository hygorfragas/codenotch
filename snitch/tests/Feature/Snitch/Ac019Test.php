<?php

use App\Models\Camera;

// SPECSFY: NFR-002 AC-019

it('nao mostra credencial da camera no historico do funcionario', function () {
    $camera = Camera::query()->firstOrFail();

    $response = $this->get('/snitch/employees/1');

    $response->assertOk();
    $response->assertDontSee($camera->credential, false);
});
