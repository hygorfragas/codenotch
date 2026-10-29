<?php

namespace App\Services;

use App\Enums\EpisodeType;
use App\Models\Alert;
use App\Models\Episode;
use Illuminate\Support\Carbon;

class AlertDispatcher
{
    private const IDLE_ONLY_CHANNELS = [
        'whatsapp-idle',
    ];

    /** @var list<string> */
    private array $lastExternalDispatches = [];

    public function dispatch(array $payload): Alert
    {
        $type = $payload['type'] ?? 'epi';
        $channels = $payload['channels'] ?? null;
        $channel = $payload['channel'] ?? null;

        $this->lastExternalDispatches = $this->resolveExternalDispatches($type, $channels, $channel);

        $episodeId = $payload['episode_id'] ?? $this->resolveEpisodeId();

        $alert = Alert::query()->create([
            'episode_id' => $episodeId,
            'channel' => $channel ?? 'panel',
            'panel_only' => $this->lastExternalDispatches === [],
            'delivered_at' => Carbon::now(),
        ]);

        $alert->syncDispatchPresentation(true, $this->lastExternalDispatches);

        return $alert;
    }

    private function resolveEpisodeId(): int
    {
        static $cachedId = null;

        if ($cachedId !== null) {
            return $cachedId;
        }

        $episode = Episode::query()->create([
            'company_id' => 1,
            'location_id' => 1,
            'employee_id' => null,
            'type' => EpisodeType::MissingPpe,
            'photo' => 'snitch/episodes/system/alert-anchor.jpg',
            'recorded_at' => Carbon::now(),
            'metadata' => ['synthetic' => true, 'purpose' => 'alert_dispatch'],
        ]);

        $cachedId = $episode->id;

        return $cachedId;
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
