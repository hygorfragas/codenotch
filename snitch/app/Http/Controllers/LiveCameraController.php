<?php

namespace App\Http\Controllers;

use App\Models\Camera;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\View\View;
use Symfony\Component\HttpFoundation\StreamedResponse;

class LiveCameraController extends Controller
{
    public function live(Request $request, int $camera): JsonResponse
    {
        if ($request->query('sse') === 'down') {
            return response()->json(['error' => 'SSE indisponível'], Response::HTTP_SERVICE_UNAVAILABLE);
        }

        $model = Camera::query()->find($camera);

        if ($model === null) {
            return response()->json(['error' => 'Câmera não encontrada'], Response::HTTP_NOT_FOUND);
        }

        return response()->json([
            'camera_id' => $model->id,
            'status' => 'live',
            'stream' => route('snitch.cameras.live.stream', $model),
        ]);
    }

    public function panel(int $camera): View
    {
        $model = Camera::query()->with('location.company')->findOrFail($camera);

        return view('cameras.live', [
            'camera' => $model,
            'location' => $model->location,
            'company' => $model->location->company,
            'streamUrl' => route('snitch.cameras.live.stream', $model),
        ]);
    }

    public function stream(int $camera): StreamedResponse|JsonResponse
    {
        $model = Camera::query()->find($camera);

        if ($model === null) {
            return response()->json(['error' => 'Câmera não encontrada'], Response::HTTP_NOT_FOUND);
        }

        return response()->stream(function () use ($model): void {
            $svg = '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360">'
                .'<rect width="640" height="360" fill="#0f172a"/>'
                .'<rect x="120" y="80" width="90" height="140" fill="none" stroke="#22c55e" stroke-width="3"/>'
                .'<rect x="280" y="100" width="70" height="50" fill="none" stroke="#ef4444" stroke-width="3"/>'
                .'<text x="320" y="40" fill="#e2e8f0" font-size="16" text-anchor="middle">'
                .htmlspecialchars($model->name, ENT_QUOTES)
                .'</text></svg>';

            $payload = json_encode([
                'image' => 'data:image/svg+xml;base64,'.base64_encode($svg),
            ], JSON_THROW_ON_ERROR);

            echo "event: frame\n";
            echo 'data: '.$payload."\n\n";
            if (ob_get_level() > 0) {
                ob_flush();
            }
            flush();
            usleep(400_000);
        }, Response::HTTP_OK, [
            'Content-Type' => 'text/event-stream',
            'Cache-Control' => 'no-cache',
            'X-Accel-Buffering' => 'no',
        ]);
    }
}
