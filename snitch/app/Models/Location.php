<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Location extends Model
{
    protected $fillable = ['company_id', 'name'];

    public function company(): BelongsTo
    {
        return $this->belongsTo(Company::class);
    }

    public function cameras(): HasMany
    {
        return $this->hasMany(Camera::class);
    }

    public function episodes(): HasMany
    {
        return $this->hasMany(Episode::class);
    }
}
