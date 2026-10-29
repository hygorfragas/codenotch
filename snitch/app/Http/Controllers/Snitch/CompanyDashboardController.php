<?php

namespace App\Http\Controllers\Snitch;

use App\Http\Controllers\Controller;
use App\Services\DashboardQuery;
use Illuminate\View\View;

class CompanyDashboardController extends Controller
{
    public function __construct(
        private readonly DashboardQuery $dashboard,
    ) {}

    public function __invoke(): View
    {
        $company = $this->dashboard->defaultCompany();
        $totals = $this->dashboard->episodeTotals($company);
        $episodes = $this->dashboard->anonymousRecentEpisodes($company);
        $locations = $company->locations()->orderBy('name')->get();

        return view('company.dashboard', [
            'company' => $company,
            'totals' => $totals,
            'episodes' => $episodes,
            'locations' => $locations,
        ]);
    }
}
