<?php

namespace App\Services;

use App\Enums\EpisodeType;
use App\Models\Employee;
use App\Models\Episode;
use App\Models\Location;
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
                type: EpisodeType::MissingPpe,
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
            type: EpisodeType::MissingPpe,
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

        return $this->persistEpisode(
            type: EpisodeType::IdleZone,
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
            type: EpisodeType::Smartphone,
            employeeId: isset($payload['employee_id']) ? (int) $payload['employee_id'] : null,
            locationId: $payload['location_id'] ?? null,
            metadata: [
                'enabled' => true,
            ],
        );
    }

    private function persistEpisode(
        EpisodeType $type,
        ?int $employeeId,
        ?int $locationId,
        array $metadata,
    ): Episode {
        $recordedAt = Carbon::now();
        [$companyId, $resolvedLocationId] = $this->resolveCompanyAndLocation($employeeId, $locationId);

        return Episode::query()->create([
            'company_id' => $companyId,
            'location_id' => $resolvedLocationId,
            'employee_id' => $employeeId,
            'type' => $type,
            'photo' => $this->capturePhotoReference($type->value, $metadata),
            'recorded_at' => $recordedAt,
            'metadata' => $metadata,
        ]);
    }

    /**
     * @return array{0: int, 1: int}
     */
    private function resolveCompanyAndLocation(?int $employeeId, ?int $locationId): array
    {
        if ($employeeId !== null) {
            $employee = Employee::query()->find($employeeId);
            if ($employee !== null) {
                $resolvedLocationId = $locationId ?? 1;

                return [$employee->company_id, (int) $resolvedLocationId];
            }
        }

        if ($locationId !== null) {
            $location = Location::query()->find($locationId);
            if ($location !== null) {
                return [$location->company_id, $location->id];
            }
        }

        return [1, 1];
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
