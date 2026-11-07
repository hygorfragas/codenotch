<?php

namespace App\Models;

use App\Enums\EpisodeType;
use Database\Factories\EpisodeFactory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Episode extends Model
{
    /** @use HasFactory<EpisodeFactory> */
    use HasFactory;

    protected $fillable = [
        'company_id',
        'location_id',
        'employee_id',
        'camera_id',
        'zone_id',
        'type',
        'photo',
        'recorded_at',
        'metadata',
    ];

    protected function casts(): array
    {
        return [
            'type' => EpisodeType::class,
            'recorded_at' => 'datetime',
            'metadata' => 'array',
        ];
    }

    public function typeLabel(): string
    {
        return match ($this->type) {
            EpisodeType::MissingPpe => 'EPI ausente',
            EpisodeType::IdleZone => $this->idleZoneLabel(),
            EpisodeType::Smartphone => 'Uso de smartphone',
        };
    }

    public function episodeSummary(): string
    {
        return match ($this->type) {
            EpisodeType::MissingPpe => $this->missingPpeSummary(),
            EpisodeType::IdleZone => $this->idleZoneSummary(),
            EpisodeType::Smartphone => $this->smartphoneSummary(),
        };
    }

    public function zoneDetail(): ?string
    {
        if ($this->type !== EpisodeType::IdleZone) {
            return null;
        }

        $meta = $this->metadata ?? [];
        $parts = [];
        $name = $meta['zone_name'] ?? $meta['zone'] ?? null;
        if (is_string($name) && $name !== '' && ! in_array($name, ['passagem', 'restrita', 'risk', 'passage'], true)) {
            $parts[] = $name;
        }
        $clock = $this->dwellClock($meta);
        if ($clock !== null) {
            $parts[] = $clock;
        }

        return $parts === [] ? null : implode(' · ', $parts);
    }

    private function missingPpeSummary(): string
    {
        $labels = $this->missingPpeLabels();
        if ($labels === []) {
            return 'EPI ausente (missing_ppe)';
        }

        return 'EPI ausente: '.implode(', ', $labels);
    }

    /**
     * @return list<string>
     */
    private function missingPpeLabels(): array
    {
        $meta = $this->metadata ?? [];
        $labels = $meta['missing_ppe_labels_pt'] ?? null;
        if (is_array($labels)) {
            $clean = [];
            foreach ($labels as $label) {
                if (is_string($label) && $label !== '') {
                    $clean[] = $label;
                }
            }
            if ($clean !== []) {
                return $clean;
            }
        }

        $items = $meta['missing_ppe'] ?? $meta['missing_items'] ?? null;
        if (is_string($items) && $items !== '') {
            $items = [$items];
        }
        if (! is_array($items) || $items === []) {
            $required = $meta['required_ppe'] ?? null;
            $detected = is_array($meta['detected_ppe'] ?? null) ? $meta['detected_ppe'] : [];
            if (is_string($required) && $required !== '' && ! in_array($required, $detected, true)) {
                $items = [$required];
            } elseif (is_array($required)) {
                $items = array_values(array_filter($required, fn (mixed $item): bool => is_string($item) && $item !== '' && ! in_array($item, $detected, true)));
            } else {
                return [];
            }
        }

        $clean = [];
        foreach ($items as $item) {
            if (is_string($item) && $item !== '') {
                $clean[] = self::ppeLabel($item);
            }
        }

        return $clean;
    }

    private function idleZoneSummary(): string
    {
        $meta = $this->metadata ?? [];
        $zoneType = $meta['zone_type'] ?? null;
        $title = in_array($zoneType, ['restrita', 'risk'], true) ? 'Zona restrita' : 'Permanência em zona';
        $name = $meta['zone_name'] ?? $meta['zone'] ?? null;
        $nameText = is_string($name) && $name !== '' && ! in_array($name, ['passagem', 'restrita', 'risk', 'passage'], true)
            ? $name
            : null;
        $clock = $this->dwellClock($meta);
        if ($nameText !== null && $clock !== null) {
            return $title.': '.$nameText.' ('.$clock.')';
        }
        if ($nameText !== null) {
            return $title.': '.$nameText;
        }
        if ($clock !== null) {
            return $title.' ('.$clock.')';
        }

        return $title.' ('.$this->type->value.')';
    }

    /**
     * @param  array<string, mixed>  $meta
     */
    private function dwellClock(array $meta): ?string
    {
        if (! isset($meta['dwell_seconds']) || ! is_numeric($meta['dwell_seconds'])) {
            return null;
        }

        $dwell = (int) $meta['dwell_seconds'];
        $max = $meta['max_time_seconds'] ?? $meta['max_dwell_seconds'] ?? null;
        if (is_numeric($max) && (int) $max > 0) {
            return $dwell.'s / '.(int) $max.'s';
        }

        return $dwell.'s';
    }

    public static function ppeLabel(string $key): string
    {
        return match ($key) {
            'helmet', 'capacete' => 'Capacete',
            'vest', 'safety-vest', 'colete' => 'Colete refletivo',
            'boots', 'botina' => 'Botina',
            'shoes' => 'Calçado de segurança',
            'gloves', 'luvas' => 'Luvas',
            'goggles', 'glasses' => 'Óculos de proteção',
            'mask', 'face-mask' => 'Máscara facial',
            'ear_protection', 'ear-mufs' => 'Protetor auricular',
            'harness' => 'Cinto de segurança',
            default => $key,
        };
    }

    private function smartphoneSummary(): string
    {
        $meta = $this->metadata ?? [];
        $seconds = $meta['smartphone_seconds'] ?? null;
        $limit = $meta['max_continuous_seconds'] ?? $meta['hand_limit_seconds'] ?? null;
        if (is_numeric($seconds) && is_numeric($limit) && (int) $limit > 0) {
            return 'Uso de smartphone: '.(int) $seconds.'s / '.(int) $limit.'s';
        }
        if (is_numeric($seconds)) {
            return 'Uso de smartphone: '.(int) $seconds.'s';
        }

        return 'Uso de smartphone (smartphone)';
    }

    private function idleZoneLabel(): string
    {
        $zoneType = ($this->metadata ?? [])['zone_type'] ?? null;
        if (in_array($zoneType, ['restrita', 'risk'], true)) {
            return 'Zona restrita';
        }

        return 'Permanência em zona';
    }

    public function thumbnailSrc(): string
    {
        $photo = (string) ($this->photo ?? '');
        if ($photo !== '' && (str_starts_with($photo, 'data:') || str_starts_with($photo, 'http://') || str_starts_with($photo, 'https://'))) {
            return $photo;
        }

        $kind = $this->type instanceof EpisodeType ? $this->type->value : 'episodio';

        return self::badgeDataUri($kind);
    }

    public static function badgeDataUri(string $kind): string
    {
        $safe = htmlspecialchars($kind, ENT_QUOTES);
        $svg = '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect width="320" height="180" fill="#0f172a"/><text x="160" y="96" fill="#34d399" font-size="18" text-anchor="middle" font-family="sans-serif">'.$safe.'</text></svg>';

        return 'data:image/svg+xml;base64,'.base64_encode($svg);
    }

    /** @return BelongsTo<Company, $this> */
    public function company(): BelongsTo
    {
        return $this->belongsTo(Company::class);
    }

    /** @return BelongsTo<Location, $this> */
    public function location(): BelongsTo
    {
        return $this->belongsTo(Location::class);
    }

    /** @return BelongsTo<Employee, $this> */
    public function employee(): BelongsTo
    {
        return $this->belongsTo(Employee::class);
    }

    /** @return BelongsTo<Camera, $this> */
    public function camera(): BelongsTo
    {
        return $this->belongsTo(Camera::class);
    }

    /** @return BelongsTo<Zone, $this> */
    public function zone(): BelongsTo
    {
        return $this->belongsTo(Zone::class);
    }

    /** @return HasMany<Alert, $this> */
    public function alerts(): HasMany
    {
        return $this->hasMany(Alert::class);
    }
}
