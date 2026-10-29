<?php

namespace App\Services;

use App\Models\Alert;

class AlertDispatcher
{
    private const IDLE_ONLY_CHANNELS = [
        'whatsapp-idle',
    ];

    public function dispatch(array $payload): Alert
    {
        $type = $payload['type'] ?? 'epi';
        $channels = $payload['channels'] ?? null;
        $channel = $payload['channel'] ?? null;

        $external = $this->resolveExternalDispatches($type, $channels, $channel);

        return Alert::query()->create([
            'type' => $type,
            'channels' => $channels,
            'channel' => $channel,
            'on_panel' => true,
            'external_dispatches' => $external,
            'episode_id' => $payload['episode_id'] ?? null,
        ]);
    }

    /**
     * @return list<string>
     */
    private function resolveExternalDispatches(string $type, mixed $channels, ?string $channel): array
    {
        if ($channels === []) {
            return [];
        }

        $targets = [];
        if (is_array($channels)) {
            $targets = $channels;
        }
        if ($channel !== null) {
            $targets[] = $channel;
        }

        $dispatched = [];
        foreach ($targets as $target) {
            if ($this->shouldSkipExternalChannel($type, $target)) {
                continue;
            }
            $dispatched[] = $target;
        }

        return $dispatched;
    }

    private function shouldSkipExternalChannel(string $type, string $channel): bool
    {
        if ($type === 'epi' && in_array($channel, self::IDLE_ONLY_CHANNELS, true)) {
            return true;
        }

        return false;
    }
}
