<?php

use App\Http\Controllers\LiveCameraController;
use App\Http\Controllers\Snitch\AlertController;
use App\Http\Controllers\Snitch\CompanyDashboardController;
use App\Http\Controllers\Snitch\EmployeeProfileController;
use App\Http\Controllers\Snitch\EpisodeController;
use App\Http\Controllers\Snitch\LocationApiController;
use App\Http\Controllers\Snitch\LocationDashboardController;
use Illuminate\Support\Facades\Route;

Route::prefix('snitch')->name('snitch.')->group(function (): void {
    Route::post('episodes/missing-ppe', [EpisodeController::class, 'missingPpe'])->name('episodes.missing-ppe');
    Route::post('episodes/idle-zone', [EpisodeController::class, 'idleZone'])->name('episodes.idle-zone');
    Route::post('episodes/smartphone', [EpisodeController::class, 'smartphone'])->name('episodes.smartphone');
    Route::post('alerts', [AlertController::class, 'store'])->name('alerts.store');

    Route::get('locations/{location}/cameras', [LocationApiController::class, 'cameras'])->name('locations.cameras');

    Route::get('cameras/{camera}/live', [LiveCameraController::class, 'live'])->name('cameras.live');
    Route::get('cameras/{camera}/live/stream', [LiveCameraController::class, 'stream'])->name('cameras.live.stream');
    Route::get('cameras/{camera}/live/painel', [LiveCameraController::class, 'panel'])->name('cameras.live.view');

    Route::get('company/dashboard', CompanyDashboardController::class)->name('company.dashboard');
    Route::get('locations/{location}', [LocationDashboardController::class, 'show'])->name('locations.show');
    Route::get('employees/{employee}', [EmployeeProfileController::class, 'show'])->name('employees.show');
});
