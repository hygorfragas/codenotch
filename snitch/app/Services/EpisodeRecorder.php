<?php

namespace App\Services;

use App\Models\Episode;
use Illuminate\Support\Carbon;

class EpisodeRecorder
{
    public function recordMissingPpe(array $payload): ?Episode
    {
        if (array_key_exists('required', $payload) && $payload['required'] === false) {
            return null;
        }

        $requiredPpe = $payload['required_ppe'] ?? null;
        if ($requiredPpe === null && ! array_key_exists('employee_id', $payload)) {
            return null;
        }

        $employeeId = $payload['employee_id'] ?? null;
        if ($employeeId === null) {
            return $this->persistEpisode(
                kind: 'missing_ppe',
                employeeId: null,
                locationId: $payload['location_id'] ?? null,
                metadata: [
                    'required_ppe' => $requiredPpe,
                    'detected_ppe' => $payload['detected_ppe'] ?? [],
                    'linked_to_employee' => false,
                ],
            );
        }

        return $this->persistEpisode(
            kind: 'missing_ppe',
            employeeId: (int) $employeeId,
            locationId: $payload['location_id'] ?? null,
            metadata: [
                'required_ppe' => $requiredPpe,
                'detected_ppe' => $payload['detected_ppe'] ?? [],
                'linked_to_employee' => true,
            ],
        );
    }

    public function recordIdleZone(array $payload): ?Episode
    {
        $zoneType = $payload['zone_type'] ?? $payload['zone'] ?? null;
        if ($zoneType !== null && $zoneType !== 'passagem') {
            return null;
        }

        $zone = $payload['zone'] ?? 'passagem';
        if ($zone !== 'passagem') {
            return null;
        }

        return $this->persistEpisode(
            kind: 'idle_zone',
            employeeId: isset($payload['employee_id']) ? (int) $payload['employee_id'] : null,
            locationId: $payload['location_id'] ?? null,
            metadata: [
                'zone' => $zone,
                'zone_type' => $zoneType ?? $zone,
            ],
        );
    }

    public function recordSmartphone(array $payload): ?Episode
    {
        if (($payload['enabled'] ?? false) !== true) {
            return null;
        }

        return $this->persistEpisode(
            kind: 'smartphone',
            employeeId: isset($payload['employee_id']) ? (int) $payload['employee_id'] : null,
            locationId: $payload['location_id'] ?? null,
            metadata: [
                'enabled' => true,
            ],
        );
    }

    private function persistEpisode(
        string $kind,
        ?int $employeeId,
        ?int $locationId,
        array $metadata,
    ): Episode {
        $recordedAt = Carbon::now();

        return Episode::query()->create([
            'employee_id' => $employeeId,
            'location_id' => $locationId,
            'kind' => $kind,
            'photo' => $this->capturePhotoReference($kind, $metadata),
            'recorded_at' => $recordedAt,
            'metadata' => $metadata,
        ]);
    }

    private function capturePhotoReference(string $kind, array $metadata): string
    {
        $stamp = Carbon::now()->format('Y-m-d\TH:i:s');

        return "snitch/episodes/{$kind}/{$stamp}.jpg";
    }

    public function episodeResponse(Episode $episode): array
    {
        return [
            'photo' => $episode->photo,
            'recorded_at' => $episode->recorded_at->toIso8601String(),
        ];
    }
}
