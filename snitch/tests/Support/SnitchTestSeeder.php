<?php

namespace Tests\Support;

use Illuminate\Support\Facades\DB;

class SnitchTestSeeder
{
    public static function seed(): void
    {
        if (DB::table('companies')->where('id', 1)->exists()) {
            return;
        }

        DB::table('companies')->insert([
            'id' => 1,
            'name' => 'Empresa Teste',
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        DB::table('locations')->insert([
            'id' => 1,
            'company_id' => 1,
            'name' => 'Localidade Teste',
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        DB::table('employees')->insert([
            'id' => 1,
            'company_id' => 1,
            'name' => 'Colaborador Teste',
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        DB::table('cameras')->insert([
            'id' => 1,
            'location_id' => 1,
            'name' => 'Camera Teste',
            'sector' => 'Acesso',
            'stream_url' => 'rtsp://example.test/stream',
            'credential' => encrypt('secret-not-in-ui'),
            'created_at' => now(),
            'updated_at' => now(),
        ]);
    }
}
