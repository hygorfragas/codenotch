<?php

namespace Database\Factories;

use App\Models\Camera;
use App\Models\Location;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<Camera>
 */
class CameraFactory extends Factory
{
    protected $model = Camera::class;

    public function definition(): array
    {
        return [
            'location_id' => Location::factory(),
            'name' => 'Câmera '.fake()->numberBetween(1, 99),
            'sector' => fake()->optional()->word(),
            'stream_url' => 'rtsp://'.fake()->ipv4().'/stream',
            'device_url' => fake()->optional()->url(),
            'credential' => null,
            'dvr_url' => null,
        ];
    }
}
