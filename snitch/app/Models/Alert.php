<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Alert extends Model
{
    protected $fillable = [
        'episode_id',
        'channel',
        'panel_only',
        'delivered_at',
    ];

    protected function casts(): array
    {
        return [
            'panel_only' => 'boolean',
            'delivered_at' => 'datetime',
        ];
    }

    /** @return BelongsTo<Episode, $this> */
    public function episode(): BelongsTo
    {
        return $this->belongsTo(Episode::class);
    }
}
