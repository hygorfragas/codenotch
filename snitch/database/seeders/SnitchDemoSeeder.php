<?php

namespace Database\Seeders;

use App\Models\Camera;
use App\Models\Company;
use App\Models\Employee;
use App\Models\Episode;
use App\Models\Location;
use Illuminate\Database\Seeder;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

class SnitchDemoSeeder extends Seeder
{
    public function run(): void
    {
        if (Company::query()->where('name', 'Obra Norte')->exists()) {
            return;
        }

        DB::transaction(function (): void {
            $this->seedDemo();
        });
    }

    private function seedDemo(): void
    {
        $company = Company::query()->create(['name' => 'Obra Norte']);

        $emptyLocation = Location::query()->create([
            'company_id' => $company->id,
            'name' => 'Galpão sem câmera',
        ]);

        $activeLocation = Location::query()->create([
            'company_id' => $company->id,
            'name' => 'Pátio principal',
        ]);

        $employee = Employee::query()->create([
            'company_id' => $company->id,
            'name' => 'Ana Silva',
        ]);

        Camera::query()->create([
            'location_id' => $activeLocation->id,
            'name' => 'Entrada oeste',
            'sector' => 'Acesso',
            'stream_url' => 'rtsp://example/stream',
            'credential' => 'secret-not-in-ui',
        ]);

        Episode::query()->create([
            'company_id' => $company->id,
            'location_id' => $activeLocation->id,
            'employee_id' => $employee->id,
            'type' => 'missing_ppe',
            'photo' => 'data:image/svg+xml;base64,PHN2Zy8+',
            'recorded_at' => Carbon::now()->subHours(2),
            'metadata' => [],
        ]);

        // Garante localidade #1 sem câmeras (AC-013).
        unset($emptyLocation);
    }
}
