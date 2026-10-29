<?php

use App\Http\Controllers\LiveCameraController;
use App\Http\Controllers\LocationCameraController;
use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return view('welcome');
});

Route::prefix('snitch')->group(function (): void {
    Route::get('cameras/{camera}/live', [LiveCameraController::class, 'show'])
        ->whereNumber('camera');
    Route::get('cameras/{camera}/stream', [LiveCameraController::class, 'stream'])
        ->whereNumber('camera');
    Route::get('locations/{location}/cameras', [LocationCameraController::class, 'index'])
        ->whereNumber('location');
});
