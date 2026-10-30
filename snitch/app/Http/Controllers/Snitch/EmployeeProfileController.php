<?php

namespace App\Http\Controllers\Snitch;

use App\Http\Controllers\Controller;
use App\Models\Employee;
use App\Models\Episode;
use App\Models\Location;
use App\Services\DashboardQuery;
use Illuminate\View\View;

class EmployeeProfileController extends Controller
{
    public function __construct(
        private readonly DashboardQuery $dashboard,
    ) {}

    public function show(int $employee): View
    {
        $model = Employee::query()
            ->with(['company'])
            ->findOrFail($employee);

        $model->setRelation('attachments', collect());

        $history = $this->dashboard->employeeHistory($model);
        $locationId = Episode::query()
            ->where('employee_id', $model->id)
            ->latest('recorded_at')
            ->value('location_id');
        $location = $locationId !== null ? Location::query()->find($locationId) : null;

        return view('employees.show', [
            'company' => $model->company,
            'location' => $location,
            'employee' => $model,
            'averages' => $this->dashboard->employeeAverages($model),
            'history' => $history,
            'latestPhoto' => $history->first()?->photo ?? $model->photo_url,
        ]);
    }
}
