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
                metadata: $this->missingPpeMetadata($payload, false),
                photo: $payload['photo'] ?? null,
                cameraId: $this->nullableForeignId($payload['camera_id'] ?? null),
            );
        }

        return $this->persistEpisode(
            type: EpisodeType::MissingPpe,
            employeeId: (int) $employeeId,
            locationId: $payload['location_id'] ?? null,
            metadata: $this->missingPpeMetadata($payload, true),
            photo: $payload['photo'] ?? null,
            cameraId: $this->nullableForeignId($payload['camera_id'] ?? null),
        );
    }

    /**
     * @param  array<string, mixed>  $payload
     * @return array<string, mixed>
     */
    private function missingPpeMetadata(array $payload, bool $linked): array
    {
        $items = $payload['missing_ppe'] ?? $payload['missing_items'] ?? null;
        if (is_string($items) && $items !== '') {
            $items = [$items];
        }
        if (! is_array($items)) {
            $required = $payload['required_ppe'] ?? null;
            $detected = is_array($payload['detected_ppe'] ?? null) ? $payload['detected_ppe'] : [];
            if (is_string($required) && $required !== '') {
                $items = in_array($required, $detected, true) ? [] : [$required];
            } elseif (is_array($required)) {
                $items = array_values(array_filter(
                    $required,
                    fn (mixed $item): bool => is_string($item) && $item !== '' && ! in_array($item, $detected, true),
                ));
            } else {
                $items = [];
            }
        }

        $clean = [];
        foreach ($items as $item) {
            if (is_string($item) && $item !== '') {
                $clean[] = $item;
            }
        }

        return [
            'required_ppe' => $payload['required_ppe'] ?? null,
            'detected_ppe' => $payload['detected_ppe'] ?? [],
            'missing_ppe' => $clean,
            'missing_items' => $clean,
            'missing_ppe_labels_pt' => $payload['missing_ppe_labels_pt'] ?? null,
            'linked_to_employee' => $linked,
        ];
    }

    public function recordIdleZone(array $payload): ?Episode
    {
        $zoneType = $payload['zone_type'] ?? null;
        if ($zoneType === null && isset($payload['zone']) && in_array($payload['zone'], ['passagem', 'restrita', 'risk'], true)) {
            $zoneType = $payload['zone'];
        }

        if (! in_array($zoneType, ['passagem', 'restrita', 'risk'], true)) {
            return null;
        }

        $exceeded = ($payload['time_exceeded'] ?? $payload['max_time_exceeded'] ?? false) === true;
        if ($zoneType === 'passagem') {
            if (! array_key_exists('max_time_seconds', $payload) || $payload['max_time_seconds'] === null || ! $exceeded) {
                return null;
            }
        } elseif (! $exceeded) {
            return null;
        }

        $zoneName = $payload['zone_name'] ?? $payload['zone'] ?? $zoneType;

        return $this->persistEpisode(
            type: EpisodeType::IdleZone,
            employeeId: $this->nullableForeignId($payload['employee_id'] ?? null),
            locationId: $payload['location_id'] ?? null,
            metadata: [
                'zone' => $zoneName,
                'zone_type' => $zoneType,
                'dwell_seconds' => isset($payload['dwell_seconds']) && is_numeric($payload['dwell_seconds'])
                    ? (int) $payload['dwell_seconds']
                    : null,
                'tracker_id' => isset($payload['tracker_id']) && is_numeric($payload['tracker_id'])
                    ? (int) $payload['tracker_id']
                    : null,
                'max_time_seconds' => $payload['max_time_seconds'] ?? null,
            ],
            photo: $payload['photo'] ?? null,
            cameraId: $this->nullableForeignId($payload['camera_id'] ?? null),
            zoneId: $this->nullableForeignId($payload['zone_id'] ?? null),
        );
    }

    public function recordSmartphone(array $payload): ?Episode
    {
        if (($payload['enabled'] ?? false) !== true) {
            return null;
        }

        if (array_key_exists('limit_exceeded', $payload) && $payload['limit_exceeded'] !== true) {
            return null;
        }

        return $this->persistEpisode(
            type: EpisodeType::Smartphone,
            employeeId: $this->nullableForeignId($payload['employee_id'] ?? null),
            locationId: $payload['location_id'] ?? null,
            metadata: [
                'enabled' => true,
                'smartphone_seconds' => isset($payload['smartphone_seconds']) && is_numeric($payload['smartphone_seconds'])
                    ? (int) $payload['smartphone_seconds']
                    : null,
                'max_continuous_seconds' => isset($payload['max_continuous_seconds']) && is_numeric($payload['max_continuous_seconds'])
                    ? (int) $payload['max_continuous_seconds']
                    : null,
                'tracker_id' => isset($payload['tracker_id']) && is_numeric($payload['tracker_id'])
                    ? (int) $payload['tracker_id']
                    : null,
            ],
            photo: $payload['photo'] ?? null,
            cameraId: $this->nullableForeignId($payload['camera_id'] ?? null),
        );
    }

    private function persistEpisode(
        EpisodeType $type,
        ?int $employeeId,
        ?int $locationId,
        array $metadata,
        ?string $photo = null,
        ?int $cameraId = null,
        ?int $zoneId = null,
    ): Episode {
        $recordedAt = Carbon::now();
        [$companyId, $resolvedLocationId] = $this->resolveCompanyAndLocation($employeeId, $locationId);

        return Episode::query()->create([
            'company_id' => $companyId,
            'location_id' => $resolvedLocationId,
            'employee_id' => $employeeId,
            'camera_id' => $cameraId,
            'zone_id' => $zoneId,
            'type' => $type,
            'photo' => $this->capturePhotoReference($type->value, $metadata, $photo),
            'recorded_at' => $recordedAt,
            'metadata' => $metadata,
        ]);
    }

    private function nullableForeignId(mixed $value): ?int
    {
        if ($value === null || $value === '' || ! is_numeric($value)) {
            return null;
        }

        $id = (int) $value;

        return $id > 0 ? $id : null;
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

    private function capturePhotoReference(string $kind, array $metadata, ?string $provided = null): string
    {
        unset($metadata);
        if (is_string($provided) && (str_starts_with($provided, 'data:image/') || str_starts_with($provided, 'http://') || str_starts_with($provided, 'https://'))) {
            return $provided;
        }

        return Episode::badgeDataUri($kind);
    }

    public function episodeResponse(Episode $episode): array
    {
        return [
            'photo' => $episode->photo,
            'recorded_at' => $episode->recorded_at->toIso8601String(),
        ];
    }
}
