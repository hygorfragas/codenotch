<?php

namespace App\Contracts;

use Symfony\Component\HttpFoundation\StreamedResponse;

interface VisionEngine
{
    public function isHealthy(): bool;

    /**
     * Proxy SSE do motor Python (imagem já com caixas).
     */
    public function streamLiveFrames(int $cameraId): StreamedResponse;
}
