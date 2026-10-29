<?php

namespace App\Services;

use Illuminate\Http\Response;

class AlertDispatcher
{
    /**
     * @param  array<string, mixed>  $payload
     * @return array{status: int, body: array<string, mixed>}
     */
    public function dispatch(array $payload): array
    {
        $type = (string) ($payload['type'] ?? 'epi');
        $channel = (string) ($payload['channel'] ?? '');
        $channels = $payload['channels'] ?? null;

        $external = [];

        if (is_array($channels) && $channels === []) {
            $external = [];
        } elseif ($channel === 'whatsapp-idle' && $type === 'epi') {
            $external = [];
        } elseif ($channel !== '') {
            $external = [$channel];
        }

        return [
            'status' => Response::HTTP_CREATED,
            'body' => [
                'panel' => true,
                'type' => $type,
                'external_channels' => $external,
            ],
        ];
    }
}
