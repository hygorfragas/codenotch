<?php

it('mostra o tempo minimo de uso de smartphone na configuracao e o contador ao vivo', function () {
    $this->get('/snitch/settings')
        ->assertOk()
        ->assertSee('Uso de smartphone')
        ->assertSee('Tempo mínimo para infração');

    $camera = \App\Models\Camera::query()->first();
    expect($camera)->not->toBeNull();

    $this->get('/snitch/cameras/'.$camera->id.'/live/painel')
        ->assertOk()
        ->assertSee('Uso de smartphone:');
});
