<?php

namespace App\Http\Controllers\Snitch;

use App\Http\Controllers\Controller;
use App\Models\Location;
use App\Services\DashboardQuery;
use Illuminate\View\View;

class LocationDashboardController extends Controller
{
    public function __construct(
        private readonly DashboardQuery $dashboard,
    ) {}

    public function show(int $location): View
    {
        $model = Location::query()
            ->with(['company', 'cameras', 'employees'])
            ->findOrFail($location);

        return view('locations.show', [
            'company' => $model->company,
            'location' => $model,
            'totals' => $this->dashboard->locationTotals($model),
            'episodes' => $this->dashboard->locationEpisodesWithEmployee($model),
            'cameras' => $model->cameras,
            'employees' => $model->employees()->orderBy('name')->get(),
        ]);
    }
}
