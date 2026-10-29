<?php

namespace App\Services;

use App\Contracts\VisionEngine;
use Illuminate\Support\Facades\Http;
use Symfony\Component\HttpFoundation\StreamedResponse;

class HttpVisionEngine implements VisionEngine
{
    public function isHealthy(): bool
    {
        $base = rtrim((string) config('snitch.vision.engine_url'), '/');
        $path = (string) config('snitch.vision.health_path');
        $timeout = (float) config('snitch.vision.connect_timeout_seconds');

        try {
            $response = Http::timeout($timeout)->get($base.$path);

            return $response->successful();
        } catch (\Throwable) {
            return false;
        }
    }

    public function streamLiveFrames(int $cameraId): StreamedResponse
    {
        $base = rtrim((string) config('snitch.vision.engine_url'), '/');
        $pathTemplate = (string) config('snitch.vision.sse_path');
        $path = str_replace('{camera}', (string) $cameraId, $pathTemplate);
        $upstream = $base.$path;

        return response()->stream(function () use ($upstream): void {
            $context = stream_context_create([
                'http' => [
                    'method' => 'GET',
                    'header' => "Accept: text/event-stream\r\n",
                    'timeout' => (float) config('snitch.vision.read_timeout_seconds'),
                ],
            ]);

            $handle = @fopen($upstream, 'r', false, $context);
            if ($handle === false) {
                echo "event: error\ndata: {\"message\":\"engine_unreachable\"}\n\n";
                if (ob_get_level() > 0) {
                    ob_flush();
                }
                flush();

                return;
            }

            while (! feof($handle)) {
                $chunk = fread($handle, 8192);
                if ($chunk === false || $chunk === '') {
                    break;
                }
                echo $chunk;
                if (ob_get_level() > 0) {
                    ob_flush();
                }
                flush();
            }

            fclose($handle);
        }, 200, [
            'Content-Type' => 'text/event-stream',
            'Cache-Control' => 'no-cache',
            'X-Accel-Buffering' => 'no',
        ]);
    }
}
