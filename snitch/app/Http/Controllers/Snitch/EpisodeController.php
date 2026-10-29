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
        $result = $this->recorder->recordMissingPpe($request->all());

        if ($result['status'] === Response::HTTP_NO_CONTENT) {
            return response()->noContent();
        }

        if ($result['status'] === Response::HTTP_ACCEPTED) {
            return response()->json(['accepted' => true], Response::HTTP_ACCEPTED);
        }

        return response()->json($result['body'], Response::HTTP_CREATED);
    }

    public function idleZone(Request $request): JsonResponse|Response
    {
        $result = $this->recorder->recordIdleZone($request->all());

        if ($result['status'] === Response::HTTP_NO_CONTENT) {
            return response()->noContent();
        }

        return response()->json($result['body'], Response::HTTP_CREATED);
    }

    public function smartphone(Request $request): JsonResponse|Response
    {
        $result = $this->recorder->recordSmartphone($request->all());

        if ($result['status'] === Response::HTTP_NO_CONTENT) {
            return response()->noContent();
        }

        return response()->json($result['body'], Response::HTTP_CREATED);
    }
}
