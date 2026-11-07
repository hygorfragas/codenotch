<?php

namespace App\Http\Controllers\Snitch;

use App\Enums\ZoneType;
use App\Http\Controllers\Controller;
use App\Models\Camera;
use App\Models\Company;
use App\Models\Employee;
use App\Models\LocationAlertChannel;
use App\Models\LocationPpeRequirement;
use App\Models\LocationSmartphoneSetting;
use App\Models\TrackerLink;
use App\Models\Zone;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;

class SettingsController extends Controller
{
    /** @var array<string, string> */
    public const PPE_CATEGORIES = [
        'helmet' => 'Capacete',
        'vest' => 'Colete refletivo',
        'boots' => 'Botina',
        'gloves' => 'Luvas',
        'goggles' => 'Óculos de proteção',
        'ear_protection' => 'Protetor auricular',
        'mask' => 'Máscara facial',
        'harness' => 'Cinto de segurança',
    ];

    public function index(): View
    {
        $company = Company::query()
            ->with([
                'locations.ppeRequirements',
                'locations.smartphoneSetting',
                'locations.alertChannels',
                'locations.cameras.zones',
                'locations.cameras.trackerLinks.employee',
                'employees',
            ])
            ->orderBy('id')
            ->first();

        return view('settings.index', [
            'company' => $company,
            'ppeCategories' => self::PPE_CATEGORIES,
            'episodeTypes' => [
                'missing_ppe' => 'EPI ausente',
                'idle_zone' => 'Permanência em zona',
                'smartphone' => 'Smartphone',
            ],
            'extraChannels' => [
                'whatsapp' => 'WhatsApp',
                'email' => 'E-mail',
                'webhook' => 'Webhook',
            ],
        ]);
    }

    public function savePpe(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'location_id' => ['required', 'integer', 'exists:locations,id'],
            'categories' => ['array'],
            'categories.*' => ['string'],
        ]);
        $selected = collect($data['categories'] ?? []);
        foreach (array_keys(self::PPE_CATEGORIES) as $category) {
            LocationPpeRequirement::query()->updateOrCreate(
                ['location_id' => $data['location_id'], 'category' => $category],
                ['required' => $selected->contains($category)],
            );
        }

        return back()->with('status', 'EPI da localidade atualizado.');
    }

    public function saveSmartphone(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'location_id' => ['required', 'integer', 'exists:locations,id'],
            'hand_limit_seconds' => ['nullable', 'integer', 'min:1', 'max:3600'],
        ]);
        LocationSmartphoneSetting::query()->updateOrCreate(
            ['location_id' => $data['location_id']],
            [
                'enabled' => $request->boolean('enabled'),
                'hand_limit_seconds' => $data['hand_limit_seconds'] ?? null,
            ],
        );

        return back()->with('status', 'Limite de smartphone atualizado.');
    }

    public function saveAlert(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'location_id' => ['required', 'integer', 'exists:locations,id'],
            'episode_type' => ['required', 'in:missing_ppe,idle_zone,smartphone'],
            'channel' => ['required', 'in:whatsapp,email,webhook'],
        ]);
        LocationAlertChannel::query()->updateOrCreate(
            [
                'location_id' => $data['location_id'],
                'episode_type' => $data['episode_type'],
                'channel' => $data['channel'],
            ],
            ['enabled' => $request->boolean('enabled')],
        );

        return back()->with('status', 'Canal de alerta atualizado.');
    }

    public function storeZone(Request $request): RedirectResponse|JsonResponse
    {
        $data = $request->validate([
            'camera_id' => ['required', 'integer', 'exists:cameras,id'],
            'name' => ['required', 'string', 'max:120'],
            'type' => ['required', 'in:passagem,restrita'],
            'max_dwell_seconds' => ['nullable', 'integer', 'min:1', 'max:86400'],
            'polygon' => ['required', 'string'],
        ]);
        $polygon = json_decode($data['polygon'], true);
        if (! is_array($polygon) || count($polygon) < 3) {
            return back()->withErrors(['polygon' => 'Informe um polígono JSON com pelo menos 3 pontos.'])->withInput();
        }
        $zone = Zone::query()->create([
            'camera_id' => $data['camera_id'],
            'name' => $data['name'],
            'type' => $data['type'],
            'max_dwell_seconds' => $data['type'] === 'passagem' ? ($data['max_dwell_seconds'] ?? null) : null,
            'polygon' => $polygon,
        ]);
        if ($request->expectsJson()) {
            return response()->json([
                'ok' => true,
                'zone' => [
                    'id' => $zone->id,
                    'name' => $zone->name,
                    'type' => $zone->type->value,
                    'max_dwell_seconds' => $zone->max_dwell_seconds,
                    'polygon' => $zone->polygon,
                ],
            ]);
        }

        return back()->with('status', 'Zona criada.');
    }

    public function destroyZone(Request $request, Zone $zone): RedirectResponse|JsonResponse
    {
        $zone->delete();
        if ($request->expectsJson()) {
            return response()->json(['ok' => true]);
        }

        return back()->with('status', 'Zona removida.');
    }

    public function storeCamera(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'location_id' => ['required', 'integer', 'exists:locations,id'],
            'name' => ['required', 'string', 'max:120'],
            'sector' => ['nullable', 'string', 'max:120'],
            'stream_url' => ['required', 'string', 'max:2048'],
            'dvr_url' => ['nullable', 'string', 'max:2048'],
        ]);
        Camera::query()->create($data);

        return back()->with('status', 'Câmera adicionada.');
    }

    public function updateCamera(Request $request, Camera $camera): RedirectResponse
    {
        $data = $request->validate([
            'name' => ['required', 'string', 'max:120'],
            'sector' => ['nullable', 'string', 'max:120'],
            'stream_url' => ['required', 'string', 'max:2048'],
            'dvr_url' => ['nullable', 'string', 'max:2048'],
        ]);
        $camera->update($data);

        return back()->with('status', 'Câmera atualizada.');
    }

    public function storeEmployee(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'company_id' => ['required', 'integer', 'exists:companies,id'],
            'name' => ['required', 'string', 'max:160'],
            'photo' => ['nullable', 'image', 'max:4096'],
        ]);
        $employee = Employee::query()->create([
            'company_id' => $data['company_id'],
            'name' => $data['name'],
        ]);
        if ($request->hasFile('photo')) {
            $employee->update([
                'photo_path' => $request->file('photo')->store('employees', 'public'),
            ]);
        }

        return back()->with('status', 'Colaborador criado.');
    }

    public function storeTrackerLink(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'camera_id' => ['required', 'integer', 'exists:cameras,id'],
            'tracker_id' => ['required', 'integer', 'min:1'],
            'employee_id' => ['required', 'integer', 'exists:employees,id'],
        ]);
        TrackerLink::query()->updateOrCreate(
            ['camera_id' => $data['camera_id'], 'tracker_id' => $data['tracker_id']],
            ['employee_id' => $data['employee_id'], 'confirmed_at' => now()],
        );

        return back()->with('status', 'Trilha vinculada ao colaborador.');
    }

    public function destroyTrackerLink(TrackerLink $trackerLink): RedirectResponse
    {
        $trackerLink->delete();

        return back()->with('status', 'Vínculo removido.');
    }

    public function engineConfig(int $camera): JsonResponse
    {
        $model = Camera::query()
            ->with(['location.ppeRequirements', 'location.smartphoneSetting', 'zones', 'trackerLinks.employee'])
            ->findOrFail($camera);
        $requirements = $model->location->ppeRequirements;
        $required = $requirements->where('required', true)->pluck('category')->values();
        if ($requirements->isEmpty()) {
            $required = collect(['helmet', 'vest', 'boots', 'gloves']);
        }
        $links = [];
        foreach ($model->trackerLinks as $link) {
            $links[(string) $link->tracker_id] = [
                'employee_id' => $link->employee_id,
                'name' => $link->employee?->name,
            ];
        }

        return response()->json([
            'camera_id' => $model->id,
            'required_ppe' => $required,
            'zones' => $model->zones->map(fn (Zone $zone): array => [
                'id' => $zone->id,
                'name' => $zone->name,
                'type' => $zone->type instanceof ZoneType ? $zone->type->value : (string) $zone->type,
                'max_dwell_seconds' => $zone->max_dwell_seconds,
                'polygon' => $zone->polygon,
            ])->values(),
            'smartphone' => [
                'enabled' => (bool) $model->location->smartphoneSetting?->enabled,
                'hand_limit_seconds' => $model->location->smartphoneSetting?->hand_limit_seconds,
            ],
            'tracker_links' => $links,
        ]);
    }
}
