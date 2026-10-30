<?php

namespace App\Models;

use Database\Factories\CameraFactory;
use Illuminate\Database\Eloquent\Casts\Attribute;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class Camera extends Model
{
    /** @use HasFactory<CameraFactory> */
    use HasFactory, SoftDeletes;

    protected static function booted(): void
    {
        static::deleting(function (Camera $camera): void {
            $camera->forceFill([
                'credential' => null,
                'dvr_url' => null,
            ])->saveQuietly();
        });
    }

    protected $fillable = [
        'location_id',
        'name',
        'sector',
        'stream_url',
        'device_url',
        'credential',
        'dvr_url',
    ];

    protected $hidden = [
        'credential',
    ];

    /** @return BelongsTo<Location, $this> */
    public function location(): BelongsTo
    {
        return $this->belongsTo(Location::class);
    }

    /** @return HasMany<Zone, $this> */
    public function zones(): HasMany
    {
        return $this->hasMany(Zone::class);
    }

    /** @return HasMany<TrackerLink, $this> */
    public function trackerLinks(): HasMany
    {
        return $this->hasMany(TrackerLink::class);
    }

    /** @return HasMany<Episode, $this> */
    public function episodes(): HasMany
    {
        return $this->hasMany(Episode::class);
    }

    /** @return Attribute<?string, ?string> */
    protected function credential(): Attribute
    {
        return Attribute::make(
            get: fn (?string $value) => $value === null ? null : decrypt($value),
            set: fn (?string $value) => $value === null ? null : encrypt($value),
        );
    }
}
