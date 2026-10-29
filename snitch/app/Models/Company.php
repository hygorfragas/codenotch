<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Company extends Model
{
    protected $fillable = ['name'];

    public function locations(): HasMany
    {
        return $this->hasMany(Location::class);
    }

    public function employees(): HasMany
    {
        return $this->hasMany(Employee::class);
    }

    public function episodes(): HasMany
    {
        return $this->hasMany(Episode::class);
    }
}
