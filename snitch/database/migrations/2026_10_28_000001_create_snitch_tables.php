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

        Schema::table('users', function (Blueprint $table) {
            $table->foreignId('company_id')->nullable()->constrained()->nullOnDelete();
            $table->foreignId('location_id')->nullable();
            $table->string('role', 32)->default('manager');
        });

        Schema::create('locations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('company_id')->constrained()->cascadeOnDelete();
            $table->string('name');
            $table->timestamps();
            $table->softDeletes();
        });

        Schema::table('users', function (Blueprint $table) {
            $table->foreign('location_id')->references('id')->on('locations')->nullOnDelete();
        });

        Schema::create('employees', function (Blueprint $table) {
            $table->id();
            $table->foreignId('company_id')->constrained()->cascadeOnDelete();
            $table->string('name');
            $table->string('photo_path')->nullable();
            $table->timestamps();

            $table->unique(['company_id', 'name']);
        });

        Schema::create('cameras', function (Blueprint $table) {
            $table->id();
            $table->foreignId('location_id')->constrained()->cascadeOnDelete();
            $table->string('name');
            $table->string('sector')->nullable();
            $table->string('stream_url');
            $table->string('device_url')->nullable();
            $table->text('credential')->nullable();
            $table->string('dvr_url')->nullable();
            $table->timestamps();
            $table->softDeletes();
        });

        Schema::create('zones', function (Blueprint $table) {
            $table->id();
            $table->foreignId('camera_id')->constrained()->cascadeOnDelete();
            $table->string('name');
            $table->string('type', 32);
            $table->unsignedInteger('max_dwell_seconds')->nullable();
            $table->json('polygon');
            $table->timestamps();
            $table->softDeletes();
        });

        Schema::create('location_ppe_requirements', function (Blueprint $table) {
            $table->id();
            $table->foreignId('location_id')->constrained()->cascadeOnDelete();
            $table->string('category');
            $table->boolean('required')->default(true);
            $table->timestamps();

            $table->unique(['location_id', 'category']);
        });

        Schema::create('location_smartphone_settings', function (Blueprint $table) {
            $table->id();
            $table->foreignId('location_id')->unique()->constrained()->cascadeOnDelete();
            $table->boolean('enabled')->default(false);
            $table->unsignedInteger('hand_limit_seconds')->nullable();
            $table->timestamps();
        });

        Schema::create('location_alert_channels', function (Blueprint $table) {
            $table->id();
            $table->foreignId('location_id')->constrained()->cascadeOnDelete();
            $table->string('episode_type', 32);
            $table->string('channel', 32);
            $table->boolean('enabled')->default(false);
            $table->json('config')->nullable();
            $table->timestamps();

            $table->unique(['location_id', 'episode_type', 'channel']);
        });

        Schema::create('tracker_links', function (Blueprint $table) {
            $table->id();
            $table->foreignId('camera_id')->constrained()->cascadeOnDelete();
            $table->unsignedInteger('tracker_id');
            $table->foreignId('employee_id')->nullable()->constrained()->nullOnDelete();
            $table->timestamp('confirmed_at')->nullable();
            $table->timestamps();

            $table->unique(['camera_id', 'tracker_id']);
        });

        Schema::create('episodes', function (Blueprint $table) {
            $table->id();
            $table->foreignId('company_id')->constrained()->cascadeOnDelete();
            $table->foreignId('location_id')->constrained()->cascadeOnDelete();
            $table->foreignId('employee_id')->nullable()->constrained()->nullOnDelete();
            $table->foreignId('camera_id')->nullable()->constrained()->nullOnDelete();
            $table->foreignId('zone_id')->nullable()->constrained()->nullOnDelete();
            $table->string('type', 32);
            $table->text('photo')->nullable();
            $table->timestamp('recorded_at');
            $table->json('metadata')->nullable();
            $table->timestamps();

            $table->index(['location_id', 'recorded_at']);
            $table->index(['employee_id', 'recorded_at']);
        });

        Schema::create('alerts', function (Blueprint $table) {
            $table->id();
            $table->foreignId('episode_id')->constrained()->cascadeOnDelete();
            $table->string('channel', 32);
            $table->boolean('panel_only')->default(false);
            $table->timestamp('delivered_at')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('alerts');
        Schema::dropIfExists('episodes');
        Schema::dropIfExists('tracker_links');
        Schema::dropIfExists('location_alert_channels');
        Schema::dropIfExists('location_smartphone_settings');
        Schema::dropIfExists('location_ppe_requirements');
        Schema::dropIfExists('zones');
        Schema::dropIfExists('cameras');
        Schema::dropIfExists('employees');

        Schema::table('users', function (Blueprint $table) {
            $table->dropForeign(['location_id']);
            $table->dropForeign(['company_id']);
            $table->dropColumn(['company_id', 'location_id', 'role']);
        });

        Schema::dropIfExists('locations');
        Schema::dropIfExists('companies');
    }
};
