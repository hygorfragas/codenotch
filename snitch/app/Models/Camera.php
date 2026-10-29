<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Camera extends Model
{
    protected $fillable = ['location_id', 'name'];

    public function location(): BelongsTo
    {
        return $this->belongsTo(Location::class);
    }
}
