<?php

namespace App\Http\Controllers\Snitch;

use App\Http\Controllers\Controller;
use App\Services\AlertDispatcher;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class AlertController extends Controller
{
    public function __construct(
        private readonly AlertDispatcher $dispatcher,
    ) {}

    public function store(Request $request): JsonResponse
    {
        $result = $this->dispatcher->dispatch($request->all());

        return response()->json($result['body'], $result['status']);
    }
}
