<?php

use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return redirect()->route('snitch.company.dashboard');
});

require __DIR__.'/snitch.php';
