<?php

namespace App\Http\Controllers\Snitch;

use App\Http\Controllers\Controller;
use App\Services\AlertDispatcher;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

class AlertController extends Controller
{
    public function __construct(
        private readonly AlertDispatcher $dispatcher,
    ) {}

    public function store(Request $request): JsonResponse
    {
        $alert = $this->dispatcher->dispatch($request->all());

        return response()->json([
            'id' => $alert->id,
            'on_panel' => $alert->on_panel,
            'external_dispatches' => $alert->external_dispatches ?? [],
        ], Response::HTTP_CREATED);
    }
}
