<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('companies', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->timestamps();
        });

        Schema::create('locations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('company_id')->constrained()->cascadeOnDelete();
            $table->string('name');
            $table->timestamps();
        });

        Schema::create('employees', function (Blueprint $table) {
            $table->id();
            $table->foreignId('company_id')->constrained()->cascadeOnDelete();
            $table->foreignId('location_id')->nullable()->constrained()->nullOnDelete();
            $table->string('name');
            $table->string('photo_url')->nullable();
            $table->timestamps();
        });

        Schema::create('cameras', function (Blueprint $table) {
            $table->id();
            $table->foreignId('location_id')->constrained()->cascadeOnDelete();
            $table->string('name');
            $table->string('sector')->nullable();
            $table->string('stream_url')->nullable();
            $table->string('device_url')->nullable();
            $table->text('credential')->nullable();
            $table->timestamps();
        });

        Schema::create('episodes', function (Blueprint $table) {
            $table->id();
            $table->foreignId('company_id')->constrained()->cascadeOnDelete();
            $table->foreignId('location_id')->constrained()->cascadeOnDelete();
            $table->foreignId('employee_id')->nullable()->constrained()->nullOnDelete();
            $table->string('type');
            $table->string('subtype')->nullable();
            $table->text('photo')->nullable();
            $table->timestamp('recorded_at');
            $table->json('metadata')->nullable();
            $table->timestamps();

            $table->index(['company_id', 'recorded_at']);
            $table->index(['location_id', 'recorded_at']);
            $table->index(['employee_id', 'recorded_at']);
        });

        Schema::create('employee_attachments', function (Blueprint $table) {
            $table->id();
            $table->foreignId('employee_id')->constrained()->cascadeOnDelete();
            $table->string('label');
            $table->string('path');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('employee_attachments');
        Schema::dropIfExists('episodes');
        Schema::dropIfExists('cameras');
        Schema::dropIfExists('employees');
        Schema::dropIfExists('locations');
        Schema::dropIfExists('companies');
    }
};
