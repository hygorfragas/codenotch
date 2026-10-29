<?php

namespace App\Services;

use App\Models\Employee;
use App\Models\Episode;
use App\Models\Location;
use Illuminate\Http\Response;
use Illuminate\Support\Carbon;

class EpisodeRecorder
{
    /**
     * @param  array<string, mixed>  $payload
     * @return array{status: int, body?: array<string, mixed>}
     */
    public function recordMissingPpe(array $payload): array
    {
        if (($payload['required'] ?? true) === false) {
            return ['status' => Response::HTTP_NO_CONTENT];
        }

        if (! array_key_exists('employee_id', $payload) || $payload['employee_id'] === null) {
            return ['status' => Response::HTTP_ACCEPTED];
        }

        $locationId = (int) ($payload['location_id'] ?? 0);
        $employeeId = (int) $payload['employee_id'];

        if ($locationId === 0 || ! Location::query()->whereKey($locationId)->exists()) {
            return ['status' => Response::HTTP_ACCEPTED];
        }

        if (! Employee::query()->whereKey($employeeId)->exists()) {
            return ['status' => Response::HTTP_ACCEPTED];
        }

        $location = Location::query()->findOrFail($locationId);
        $recordedAt = Carbon::now();
        $photo = $this->placeholderPhoto('epi', $payload['required_ppe'] ?? 'epi');

        $episode = Episode::query()->create([
            'company_id' => $location->company_id,
            'location_id' => $location->id,
            'employee_id' => $employeeId,
            'type' => Episode::TYPE_EPI,
            'subtype' => (string) ($payload['required_ppe'] ?? 'epi'),
            'photo' => $photo,
            'recorded_at' => $recordedAt,
            'metadata' => [
                'detected_ppe' => $payload['detected_ppe'] ?? [],
            ],
        ]);

        return [
            'status' => Response::HTTP_CREATED,
            'body' => [
                'photo' => $episode->photo,
                'recorded_at' => $episode->recorded_at->toIso8601String(),
            ],
        ];
    }

    /**
     * @param  array<string, mixed>  $payload
     * @return array{status: int, body?: array<string, mixed>}
     */
    public function recordIdleZone(array $payload): array
    {
        $zoneType = (string) ($payload['zone_type'] ?? $payload['zone'] ?? '');

        if ($zoneType !== 'passagem') {
            return ['status' => Response::HTTP_NO_CONTENT];
        }

        $employeeId = (int) ($payload['employee_id'] ?? 0);
        $employee = Employee::query()->find($employeeId);

        if ($employee === null || $employee->location_id === null) {
            return ['status' => Response::HTTP_NO_CONTENT];
        }

        $recordedAt = Carbon::now();
        $photo = $this->placeholderPhoto('idle', $zoneType);

        $episode = Episode::query()->create([
            'company_id' => $employee->company_id,
            'location_id' => $employee->location_id,
            'employee_id' => $employee->id,
            'type' => Episode::TYPE_IDLE,
            'subtype' => $zoneType,
            'photo' => $photo,
            'recorded_at' => $recordedAt,
            'metadata' => [
                'zone' => $payload['zone'] ?? $zoneType,
            ],
        ]);

        return [
            'status' => Response::HTTP_CREATED,
            'body' => [
                'photo' => $episode->photo,
                'recorded_at' => $episode->recorded_at->toIso8601String(),
            ],
        ];
    }

    /**
     * @param  array<string, mixed>  $payload
     * @return array{status: int, body?: array<string, mixed>}
     */
    public function recordSmartphone(array $payload): array
    {
        if (($payload['enabled'] ?? false) !== true) {
            return ['status' => Response::HTTP_NO_CONTENT];
        }

        $employeeId = (int) ($payload['employee_id'] ?? 0);
        $employee = Employee::query()->find($employeeId);

        if ($employee === null || $employee->location_id === null) {
            return ['status' => Response::HTTP_NO_CONTENT];
        }

        $recordedAt = Carbon::now();
        $photo = $this->placeholderPhoto('idle', 'smartphone');

        $episode = Episode::query()->create([
            'company_id' => $employee->company_id,
            'location_id' => $employee->location_id,
            'employee_id' => $employee->id,
            'type' => Episode::TYPE_IDLE,
            'subtype' => 'smartphone',
            'photo' => $photo,
            'recorded_at' => $recordedAt,
            'metadata' => ['source' => 'smartphone'],
        ]);

        return [
            'status' => Response::HTTP_CREATED,
            'body' => [
                'photo' => $episode->photo,
                'recorded_at' => $episode->recorded_at->toIso8601String(),
            ],
        ];
    }

    private function placeholderPhoto(string $kind, string $label): string
    {
        return 'data:image/svg+xml;base64,'.base64_encode(
            '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180">'
            .'<rect width="320" height="180" fill="#1e293b"/>'
            .'<text x="160" y="90" fill="#94a3b8" font-size="14" text-anchor="middle">'
            .htmlspecialchars(strtoupper($kind).' · '.$label, ENT_QUOTES)
            .'</text></svg>'
        );
    }
}
