<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;

/**
 * Listagem de câmeras por localidade.
 *
 * T022 (migrations) ainda não aplicada neste segmento — retorna lista vazia (AC-013).
 */
class LocationCameraController extends Controller
{
    public function index(int $location): JsonResponse
    {
        return response()->json([
            'location_id' => $location,
            'data' => [],
        ]);
    }
}
