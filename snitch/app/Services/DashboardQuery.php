<?php

namespace App\Services;

use App\Models\Company;
use App\Models\Employee;
use App\Models\Episode;
use App\Models\Location;
use Illuminate\Support\Carbon;
use Illuminate\Support\Collection;

class DashboardQuery
{
    public function defaultCompany(): Company
    {
        return Company::query()->firstOrFail();
    }

    /**
     * @return array{day: int, month: int}
     */
    public function episodeTotals(Company $company): array
    {
        $now = Carbon::now();

        return [
            'day' => Episode::query()
                ->where('company_id', $company->id)
                ->whereDate('recorded_at', $now->toDateString())
                ->count(),
            'month' => Episode::query()
                ->where('company_id', $company->id)
                ->whereMonth('recorded_at', $now->month)
                ->whereYear('recorded_at', $now->year)
                ->count(),
        ];
    }

    /**
     * Episodes for global dashboard — no employee name.
     *
     * @return Collection<int, Episode>
     */
    public function anonymousRecentEpisodes(Company $company, int $limit = 12): Collection
    {
        return Episode::query()
            ->where('company_id', $company->id)
            ->latest('recorded_at')
            ->limit($limit)
            ->get();
    }

    /**
     * @return array{day: int, month: int}
     */
    public function locationTotals(Location $location): array
    {
        $now = Carbon::now();

        return [
            'day' => Episode::query()
                ->where('location_id', $location->id)
                ->whereDate('recorded_at', $now->toDateString())
                ->count(),
            'month' => Episode::query()
                ->where('location_id', $location->id)
                ->whereMonth('recorded_at', $now->month)
                ->whereYear('recorded_at', $now->year)
                ->count(),
        ];
    }

    /**
     * @return Collection<int, Episode>
     */
    public function locationEpisodesWithEmployee(Location $location, int $limit = 12): Collection
    {
        return Episode::query()
            ->with('employee')
            ->where('location_id', $location->id)
            ->latest('recorded_at')
            ->limit($limit)
            ->get();
    }

    /**
     * @return array{day_avg: float, month_avg: float}
     */
    public function employeeAverages(Employee $employee): array
    {
        $now = Carbon::now();

        $dayCount = Episode::query()
            ->where('employee_id', $employee->id)
            ->whereDate('recorded_at', $now->toDateString())
            ->count();

        $monthCount = Episode::query()
            ->where('employee_id', $employee->id)
            ->whereMonth('recorded_at', $now->month)
            ->whereYear('recorded_at', $now->year)
            ->count();

        $daysInMonth = max(1, (int) $now->format('j'));

        return [
            'day_avg' => round($dayCount, 1),
            'month_avg' => round($monthCount / $daysInMonth, 1),
        ];
    }

    /**
     * @return Collection<int, Episode>
     */
    public function employeeHistory(Employee $employee, int $limit = 20): Collection
    {
        return Episode::query()
            ->where('employee_id', $employee->id)
            ->latest('recorded_at')
            ->limit($limit)
            ->get();
    }
}
