<?php

namespace Database\Seeders;

use App\Models\Camera;
use App\Models\Company;
use App\Models\Employee;
use App\Models\EmployeeAttachment;
use App\Models\Episode;
use App\Models\Location;
use Illuminate\Database\Seeder;
use Illuminate\Support\Carbon;

class SnitchDemoSeeder extends Seeder
{
    public function run(): void
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
            'location_id' => $activeLocation->id,
            'name' => 'Ana Silva',
        ]);

        EmployeeAttachment::query()->create([
            'employee_id' => $employee->id,
            'label' => 'ASO',
            'path' => 'anexos/aso-ana.pdf',
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
            'type' => 'epi',
            'subtype' => 'capacete',
            'photo' => 'data:image/svg+xml;base64,PHN2Zy8+',
            'recorded_at' => Carbon::now()->subHours(2),
            'metadata' => [],
        ]);

        // Garante localidade #1 sem câmeras (AC-013).
        unset($emptyLocation);
    }
}
