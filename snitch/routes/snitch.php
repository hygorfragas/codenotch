<?php

use App\Http\Controllers\LiveCameraController;
use App\Http\Controllers\Snitch\AlertController;
use App\Http\Controllers\Snitch\CompanyDashboardController;
use App\Http\Controllers\Snitch\EmployeeProfileController;
use App\Http\Controllers\Snitch\EpisodeController;
use App\Http\Controllers\Snitch\LocationApiController;
use App\Http\Controllers\Snitch\LocationDashboardController;
use App\Http\Controllers\Snitch\SettingsController;
use Illuminate\Support\Facades\Route;

Route::prefix('snitch')->name('snitch.')->group(function (): void {
    Route::get('settings', [SettingsController::class, 'index'])->name('settings.index');
    Route::post('settings/ppe', [SettingsController::class, 'savePpe'])->name('settings.ppe');
    Route::post('settings/smartphone', [SettingsController::class, 'saveSmartphone'])->name('settings.smartphone');
    Route::post('settings/alerts', [SettingsController::class, 'saveAlert'])->name('settings.alerts');
    Route::post('settings/zones', [SettingsController::class, 'storeZone'])->name('settings.zones.store');
    Route::delete('settings/zones/{zone}', [SettingsController::class, 'destroyZone'])->name('settings.zones.destroy');
    Route::post('settings/cameras', [SettingsController::class, 'storeCamera'])->name('settings.cameras.store');
    Route::put('settings/cameras/{camera}', [SettingsController::class, 'updateCamera'])->name('settings.cameras.update');
    Route::post('settings/employees', [SettingsController::class, 'storeEmployee'])->name('settings.employees.store');
    Route::post('settings/tracker-links', [SettingsController::class, 'storeTrackerLink'])->name('settings.tracker-links.store');
    Route::delete('settings/tracker-links/{trackerLink}', [SettingsController::class, 'destroyTrackerLink'])->name('settings.tracker-links.destroy');

    Route::post('episodes/ppe', [EpisodeController::class, 'missingPpe'])->name('episodes.ppe');
    Route::post('episodes/missing-ppe', [EpisodeController::class, 'missingPpe'])->name('episodes.missing-ppe');
    Route::post('episodes/idle-zone', [EpisodeController::class, 'idleZone'])->name('episodes.idle-zone');
    Route::post('episodes/smartphone', [EpisodeController::class, 'smartphone'])->name('episodes.smartphone');
    Route::post('alerts', [AlertController::class, 'store'])->name('alerts.store');

    Route::get('locations/{location}/cameras', [LocationApiController::class, 'cameras'])
        ->whereNumber('location')
        ->name('locations.cameras');

    Route::get('cameras/{camera}/live', [LiveCameraController::class, 'show'])
        ->whereNumber('camera')
        ->name('cameras.live');
    Route::get('cameras/{camera}/stream', [LiveCameraController::class, 'stream'])
        ->whereNumber('camera')
        ->name('cameras.stream');
    Route::get('cameras/{camera}/live/painel', [LiveCameraController::class, 'panel'])
        ->whereNumber('camera')
        ->name('cameras.live.view');
    Route::get('cameras/{camera}/engine-config', [SettingsController::class, 'engineConfig'])
        ->whereNumber('camera')
        ->name('cameras.engine-config');

    Route::get('company/dashboard', CompanyDashboardController::class)->name('company.dashboard');
    Route::get('locations/{location}', [LocationDashboardController::class, 'show'])
        ->whereNumber('location')
        ->name('locations.show');
    Route::get('employees/{employee}', [EmployeeProfileController::class, 'show'])
        ->whereNumber('employee')
        ->name('employees.show');
});
