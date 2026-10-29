<?php

use App\Http\Controllers\Snitch\AlertController;
use App\Http\Controllers\Snitch\EpisodeController;
use Illuminate\Support\Facades\Route;

Route::prefix('snitch')->group(function (): void {
    Route::post('episodes/missing-ppe', [EpisodeController::class, 'missingPpe']);
    Route::post('episodes/idle-zone', [EpisodeController::class, 'idleZone']);
    Route::post('episodes/smartphone', [EpisodeController::class, 'smartphone']);
    Route::post('alerts', [AlertController::class, 'store']);
});
