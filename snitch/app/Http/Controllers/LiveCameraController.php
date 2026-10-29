<?php

namespace App\Http\Controllers;

use App\Contracts\VisionEngine;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\StreamedResponse;

class LiveCameraController extends Controller
{
    public function __construct(
        private readonly VisionEngine $visionEngine,
    ) {}

    /**
     * Ao vivo: proxy SSE ou metadados JSON. Não grava episódio (FR-004 / AC-004).
     */
    public function show(Request $request, int $camera): JsonResponse|StreamedResponse
    {
        if ($request->query('sse') === 'down') {
            return response()->json([
                'message' => 'SSE indisponível',
            ], 503);
        }

        if ($request->accepts('text/event-stream') && ! $request->expectsJson()) {
            if (! $this->visionEngine->isHealthy()) {
                return response()->json([
                    'message' => 'Motor de visão indisponível',
                ], 503);
            }

            return $this->visionEngine->streamLiveFrames($camera);
        }

        return response()->json([
            'camera_id' => $camera,
            'creates_records' => false,
            'stream' => [
                'type' => 'sse',
                'url' => url("/snitch/cameras/{$camera}/stream"),
            ],
        ]);
    }

    /**
     * Fluxo SSE dedicado (imagem com caixas vindas do Python).
     */
    public function stream(Request $request, int $camera): StreamedResponse|JsonResponse
    {
        if ($request->query('sse') === 'down') {
            return response()->json([
                'message' => 'SSE indisponível',
            ], 503);
        }

        if (! $this->visionEngine->isHealthy()) {
            return response()->json([
                'message' => 'Motor de visão indisponível',
            ], 503);
        }

        return $this->visionEngine->streamLiveFrames($camera);
    }
}
