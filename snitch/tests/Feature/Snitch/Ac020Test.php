<?php

use App\Models\Camera;
use App\Models\Episode;

// SPECSFY: NFR-002 AC-020

it('remove credencial ao apagar camera e mantem historico de epi', function () {
    $camera = Camera::query()->firstOrFail();
    $camera->update(['credential' => 'credencial-admin-apaga']);

    $historyBefore = Episode::query()->count();

    $camera->delete();

    $trashed = Camera::withTrashed()->findOrFail($camera->id);

    expect($trashed->credential)->toBeNull()
        ->and(Episode::query()->count())->toBe($historyBefore);
});
