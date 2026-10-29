<?php

namespace App\Http\Controllers\Snitch;

use App\Http\Controllers\Controller;
use App\Services\EpisodeRecorder;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

class EpisodeController extends Controller
{
    public function __construct(
        private readonly EpisodeRecorder $recorder,
    ) {}

    public function missingPpe(Request $request): JsonResponse|Response
    {
        $payload = $request->all();
        $episode = $this->recorder->recordMissingPpe($payload);

        if ($episode === null) {
            return response()->noContent();
        }

        if (($payload['employee_id'] ?? null) === null) {
            return response()->json($this->recorder->episodeResponse($episode), Response::HTTP_ACCEPTED);
        }

        return response()->json($this->recorder->episodeResponse($episode), Response::HTTP_CREATED);
    }

    public function idleZone(Request $request): JsonResponse|Response
    {
        $episode = $this->recorder->recordIdleZone($request->all());

        if ($episode === null) {
            return response()->noContent();
        }

        return response()->json($this->recorder->episodeResponse($episode), Response::HTTP_CREATED);
    }

    public function smartphone(Request $request): JsonResponse|Response
    {
        $episode = $this->recorder->recordSmartphone($request->all());

        if ($episode === null) {
            return response()->noContent();
        }

        return response()->json($this->recorder->episodeResponse($episode), Response::HTTP_CREATED);
    }
}
