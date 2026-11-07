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
            EpisodeType::IdleZone => 'Ociosidade na zona',
            EpisodeType::Smartphone => 'Uso de smartphone',
        };
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
