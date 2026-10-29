<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class EmployeeAttachment extends Model
{
    protected $fillable = ['employee_id', 'label', 'path'];

    public function employee(): BelongsTo
    {
        return $this->belongsTo(Employee::class);
    }
}
