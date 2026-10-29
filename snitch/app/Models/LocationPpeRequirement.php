<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class LocationPpeRequirement extends Model
{
    protected $fillable = [
        'location_id',
        'category',
        'required',
    ];

    protected function casts(): array
    {
        return [
            'required' => 'boolean',
        ];
    }

    /** @return BelongsTo<Location, $this> */
    public function location(): BelongsTo
    {
        return $this->belongsTo(Location::class);
    }
}
