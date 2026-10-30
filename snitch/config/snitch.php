<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Motor de visão (Python)
    |--------------------------------------------------------------------------
    |
    | O processo Python expõe SSE com frames anotados e aceita consultas Jev
    | via JSON de estado. Laravel faz proxy do SSE para o painel.
    |
    */

    'deployment' => [
        'colocated' => filter_var(env('SNITCH_COLOCATED', true), FILTER_VALIDATE_BOOL),
    ],

    'vision' => [
        'engine_url' => env('SNITCH_ENGINE_URL', 'http://127.0.0.1:8765'),
        'sse_path' => env('SNITCH_ENGINE_SSE_PATH', '/cameras/{camera}/stream'),
        'health_path' => env('SNITCH_ENGINE_HEALTH_PATH', '/health'),
        'connect_timeout_seconds' => (float) env('SNITCH_ENGINE_CONNECT_TIMEOUT', 2),
        'read_timeout_seconds' => (float) env('SNITCH_ENGINE_READ_TIMEOUT', 0),
    ],

    'weights' => [
        'sh17' => env('SH17_WEIGHTS', base_path('storage/engine/sh17.pt')),
    ],

];
