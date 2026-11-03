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
@endsection

@push('scripts')
    <script>
        (() => {
            const frame = document.getElementById('live-frame');
            const status = document.getElementById('live-status');
            const decisions = document.getElementById('live-decisions');
            const errorBox = document.getElementById('live-error');
            const placeholder = document.getElementById('live-placeholder');
            const streamUrl = @json($streamUrl);
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
