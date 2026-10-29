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

    protected $appends = [
        'on_panel',
        'external_dispatches',
    ];

    private bool $presentationOnPanel = true;

    /** @var list<string> */
    private array $presentationExternalDispatches = [];

    protected function casts(): array
    {
        return [
            'panel_only' => 'boolean',
            'delivered_at' => 'datetime',
        ];
    }

    /**
     * @param  list<string>  $externalDispatches
     */
    public function syncDispatchPresentation(bool $onPanel, array $externalDispatches): void
    {
        $this->presentationOnPanel = $onPanel;
        $this->presentationExternalDispatches = $externalDispatches;
    }

    public function getOnPanelAttribute(): bool
    {
        return $this->presentationOnPanel;
    }

    /**
     * @return list<string>
     */
    public function getExternalDispatchesAttribute(): array
    {
        return $this->presentationExternalDispatches;
    }

    /** @return BelongsTo<Episode, $this> */
    public function episode(): BelongsTo
    {
        return $this->belongsTo(Episode::class);
    }
}
