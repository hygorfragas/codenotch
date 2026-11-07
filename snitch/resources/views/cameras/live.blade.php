@extends('layouts.snitch')

@section('title', 'Câmera '.$camera->name)
@section('heading', 'Câmera ao vivo')

@section('breadcrumb')
    <ol class="flex flex-wrap items-center gap-2">
        <li><a href="{{ route('snitch.company.dashboard') }}" class="hover:text-emerald-400">{{ $company->name }}</a></li>
        <li class="text-slate-500" aria-hidden="true">/</li>
        <li><a href="{{ route('snitch.locations.show', $location) }}" class="hover:text-emerald-400">{{ $location->name }}</a></li>
        <li class="text-slate-500" aria-hidden="true">/</li>
        <li><span class="font-medium text-slate-200" aria-current="page">{{ $camera->name }}</span></li>
    </ol>
@endsection

@section('content')
    <section class="rounded-xl border border-slate-800 bg-slate-900/50 p-4 sm:p-6">
        <div class="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
                <h2 class="text-lg font-semibold text-white">{{ $camera->name }}</h2>
                <p class="text-sm text-slate-400">Imagem com caixas via SSE — abrir a câmera não cria registro.</p>
            </div>
            <p id="live-status" class="text-sm font-medium text-emerald-400" role="status">Conectando…</p>
        </div>
        <p id="live-telemetry" class="mb-1 text-sm text-slate-300">FPS — · quadro — · Laya aguardando</p>
        <p id="live-decisions" class="mb-4 text-sm text-slate-300"></p>

        <div class="relative aspect-video overflow-hidden rounded-lg border border-slate-700 bg-slate-950">
            <img id="live-frame" alt="Fluxo ao vivo com caixas de detecção" class="h-full w-full object-contain" hidden>
            <div id="live-error" class="absolute inset-0 hidden flex-col items-center justify-center gap-2 bg-slate-950/90 p-6 text-center" role="alert">
                <p class="text-base font-semibold text-red-400">Erro no envio ao vivo</p>
                <p class="text-sm text-slate-400">O registro já gravado permanece. Tente recarregar quando o SSE voltar.</p>
            </div>
            <div id="live-placeholder" class="absolute inset-0 flex items-center justify-center text-sm text-slate-500">
                Aguardando quadro…
            </div>
        </div>
    </section>

    <x-engine-status />

    <section class="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <h2 class="text-sm font-semibold text-white">Vincular trilha a um colaborador</h2>
        <p class="mt-1 text-sm text-slate-400">O número aparece na caixa, por exemplo Track #1. Depois do vínculo a caixa mostra [#1 Nome].</p>
        <ul class="mt-3 space-y-1 text-sm text-slate-300">
            @foreach ($trackerLinks as $link)
                <li>Track #{{ $link->tracker_id }} → {{ $link->employee?->name ?? 'sem nome' }}</li>
            @endforeach
        </ul>
        <form method="post" action="{{ route('snitch.settings.tracker-links.store') }}" class="mt-3 flex flex-wrap items-end gap-2">
            @csrf
            <input type="hidden" name="camera_id" value="{{ $camera->id }}">
            <label class="text-sm text-slate-300">Track
                <input type="number" name="tracker_id" min="1" required class="mt-1 block w-24 rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
            </label>
            <label class="text-sm text-slate-300">Colaborador
                <select name="employee_id" required class="mt-1 block rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                    @foreach ($employees as $employee)
                        <option value="{{ $employee->id }}">{{ $employee->name }}</option>
                    @endforeach
                </select>
            </label>
            <button class="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white">Vincular</button>
        </form>
    </section>
@endsection

@push('scripts')
    <script>
        (() => {
            const frame = document.getElementById('live-frame');
            const status = document.getElementById('live-status');
            const decisions = document.getElementById('live-decisions');
            const telemetry = document.getElementById('live-telemetry');
            let lastFrameAt = 0;
            let frames = 0;
            let fpsStamp = performance.now();
            const errorBox = document.getElementById('live-error');
            const placeholder = document.getElementById('live-placeholder');
            const streamUrl = @json($engineStreamUrl ?? $streamUrl);
            const jevLabels = {
                any_missing_required_ppe: 'EPI obrigatório faltando',
                any_person_in_restricted_zone: 'Pessoa em zona restrita',
            };

            const source = new EventSource(streamUrl);

            source.addEventListener('frame', (event) => {
                try {
                    const payload = JSON.parse(event.data);
                    const jpeg = payload.image
                        || (payload.image_jpeg_base64
                            ? `data:image/jpeg;base64,${payload.image_jpeg_base64}`
                            : null);
                    if (jpeg) {
                        frame.src = jpeg;
                        frame.hidden = false;
                        placeholder.classList.add('hidden');
                        errorBox.classList.add('hidden');
                        errorBox.classList.remove('flex');
                        status.textContent = 'Ao vivo';
                        status.className = 'text-sm font-medium text-emerald-400';
                        frames += 1;
                        const now = performance.now();
                        const elapsed = (now - fpsStamp) / 1000;
                        const localFps = elapsed > 0 ? (frames / elapsed).toFixed(1) : '0.0';
                        const info = (payload.state && payload.state.telemetry) || {};
                        const laya = info.laya_engine || 'aguardando';
                        const latency = info.jev_latency_ms == null ? '—' : `${Math.round(info.jev_latency_ms)} ms`;
                        const updated = info.jev_updated_at ? new Date(info.jev_updated_at * 1000).toLocaleTimeString() : '—';
                        telemetry.textContent = `FPS ${info.fps ?? localFps} · quadro ${info.frame_index ?? frames} · Laya ${laya} · ${latency} · atualizado ${updated}`;
                        lastFrameAt = now;
                    }
                    const jev = payload.state && payload.state.jev;
                    if (jev && typeof jev === 'object') {
                        decisions.textContent = Object.entries(jev).map(([key, value]) => {
                            const label = jevLabels[key] || key;
                            const text = value === true ? 'sim' : value === false ? 'não' : String(value);
                            return `${label}: ${text}`;
                        }).join(' · ');
                    } else if (payload.state && payload.state.jev_error) {
                        decisions.textContent = 'Jev sem resposta neste quadro';
                    }
                } catch {
                    showError();
                }
            });

            source.onerror = () => {
                showError();
                source.close();
            };

            function showError() {
                status.textContent = 'SSE indisponível';
                status.className = 'text-sm font-medium text-red-400';
                errorBox.classList.remove('hidden');
                errorBox.classList.add('flex');
            }
        })();
    </script>
@endpush
