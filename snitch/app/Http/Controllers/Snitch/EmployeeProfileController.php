<?php

namespace App\Http\Controllers\Snitch;

use App\Http\Controllers\Controller;
use App\Models\Employee;
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
            ->with(['company', 'location', 'attachments'])
            ->findOrFail($employee);

        $history = $this->dashboard->employeeHistory($model);

        return view('employees.show', [
            'company' => $model->company,
            'location' => $model->location,
            'employee' => $model,
            'averages' => $this->dashboard->employeeAverages($model),
            'history' => $history,
            'latestPhoto' => $history->first()?->photo ?? $model->photo_url,
        ]);
    }
}
