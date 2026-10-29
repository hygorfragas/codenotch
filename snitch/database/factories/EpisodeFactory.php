<?php

namespace Database\Factories;

use App\Enums\EpisodeType;
use App\Models\Company;
use App\Models\Employee;
use App\Models\Episode;
use App\Models\Location;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<Episode>
 */
class EpisodeFactory extends Factory
{
    protected $model = Episode::class;

    public function definition(): array
    {
        $company = Company::factory();

        return [
            'company_id' => $company,
            'location_id' => Location::factory()->for($company),
            'employee_id' => Employee::factory()->for($company),
            'camera_id' => null,
            'zone_id' => null,
            'type' => EpisodeType::MissingPpe,
            'photo' => base64_encode('fake-image'),
            'recorded_at' => now(),
            'metadata' => ['required_ppe' => 'capacete'],
        ];
    }
}
