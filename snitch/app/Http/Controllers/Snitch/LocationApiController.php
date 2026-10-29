<?php

namespace App\Http\Controllers\Snitch;

use App\Http\Controllers\Controller;
use App\Models\Location;
use Illuminate\Http\JsonResponse;

class LocationApiController extends Controller
{
    public function cameras(int $location): JsonResponse
    {
        $model = Location::query()->find($location);

        if ($model === null) {
            return response()->json(['data' => []]);
        }

        $cameras = $model->cameras()
            ->get(['id', 'name', 'sector'])
            ->map(fn ($camera) => [
                'id' => $camera->id,
                'name' => $camera->name,
                'sector' => $camera->sector,
            ]);

        return response()->json(['data' => $cameras]);
    }
}
