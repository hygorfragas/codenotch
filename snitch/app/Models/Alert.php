<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Alert extends Model
{
    protected $fillable = [
        'episode_id',
        'type',
        'channels',
        'channel',
        'on_panel',
        'external_dispatches',
    ];

    protected function casts(): array
    {
        return [
            'channels' => 'array',
            'on_panel' => 'boolean',
            'external_dispatches' => 'array',
        ];
    }

    public function episode(): BelongsTo
    {
        return $this->belongsTo(Episode::class);
    }
}
