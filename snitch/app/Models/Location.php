<?php

namespace App\Models;

use Database\Factories\LocationFactory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\HasOne;
use Illuminate\Database\Eloquent\SoftDeletes;

class Location extends Model
{
    /** @use HasFactory<LocationFactory> */
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'company_id',
        'name',
    ];

    /** @return BelongsTo<Company, $this> */
    public function company(): BelongsTo
    {
        return $this->belongsTo(Company::class);
    }

    /** @return HasMany<Camera, $this> */
    public function cameras(): HasMany
    {
        return $this->hasMany(Camera::class);
    }

    /** @return HasMany<Episode, $this> */
    public function episodes(): HasMany
    {
        return $this->hasMany(Episode::class);
    }

    /** @return HasMany<LocationPpeRequirement, $this> */
    public function ppeRequirements(): HasMany
    {
        return $this->hasMany(LocationPpeRequirement::class);
    }

    /** @return HasOne<LocationSmartphoneSetting, $this> */
    public function smartphoneSetting(): HasOne
    {
        return $this->hasOne(LocationSmartphoneSetting::class);
    }

    /** @return HasMany<LocationAlertChannel, $this> */
    public function alertChannels(): HasMany
    {
        return $this->hasMany(LocationAlertChannel::class);
    }

    /** @return HasMany<User, $this> */
    public function managers(): HasMany
    {
        return $this->hasMany(User::class);
    }
}
