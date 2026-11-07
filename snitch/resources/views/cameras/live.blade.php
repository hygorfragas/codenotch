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
        <p id="live-telemetry" class="mb-1 text-sm text-slate-300">FPS — · Memória: último quadro (sem acúmulo) · Laya aguardando</p>
        <p id="live-decisions" class="mb-1 text-sm text-slate-300"></p>
        <p id="live-zones" class="mb-4 text-sm text-slate-300">Zonas: aguardando permanência…</p>

        <div id="live-stage" class="relative aspect-video overflow-hidden rounded-lg border border-slate-700 bg-slate-950">
            <img id="live-frame" alt="Fluxo ao vivo com caixas de detecção" class="h-full w-full object-contain" hidden>
            <canvas id="zone-canvas" class="absolute inset-0 h-full w-full"></canvas>
            <div id="live-error" class="absolute inset-0 hidden flex-col items-center justify-center gap-2 bg-slate-950/90 p-6 text-center" role="alert">
                <p class="text-base font-semibold text-red-400">Erro no envio ao vivo</p>
                <p class="text-sm text-slate-400">O registro já gravado permanece. Tente recarregar quando o SSE voltar.</p>
            </div>
            <div id="live-placeholder" class="absolute inset-0 flex items-center justify-center text-sm text-slate-500">
                Aguardando quadro…
            </div>
        </div>
    </section>

    <section class="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <div class="flex flex-wrap items-end gap-3">
            <h2 class="text-sm font-semibold text-white">Zona nesta câmera</h2>
            <button type="button" id="zone-draw" class="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white">Desenhar nova zona</button>
            <button type="button" id="zone-undo" class="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-200">Desfazer ponto</button>
        </div>
        <form id="zone-form" class="mt-3 grid gap-3 md:grid-cols-4">
            <label class="text-sm text-slate-300">Nome
                <input id="zone-name" required class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1" placeholder="Corredor">
            </label>
            <label class="text-sm text-slate-300">Tipo
                <select id="zone-type" class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                    <option value="passagem">Passagem</option>
                    <option value="restrita">Restrita</option>
                </select>
            </label>
            <label class="text-sm text-slate-300">Tempo máx. ocioso (s)
                <input id="zone-dwell" type="number" min="1" class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1" placeholder="30">
            </label>
            <button id="zone-save" type="button" class="self-end rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white">Salvar zona</button>
        </form>
        <ul id="zone-list" class="mt-3 space-y-1 text-sm text-slate-300"></ul>
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
                        telemetry.textContent = `FPS ${info.fps ?? localFps} · Memória: último quadro (sem acúmulo) · Laya ${laya} · ${latency} · atualizado ${updated}`;
                        lastFrameAt = now;
                    }
                    const jev = payload.state && payload.state.jev;
                    const missingLabels = (payload.state && payload.state.missing_ppe_labels_pt) || [];
                    if ((jev && typeof jev === 'object') || missingLabels.length) {
                        const parts = [];
                        if (missingLabels.length) {
                            parts.push(`EPI ausente: ${missingLabels.join(', ')}`);
                            parts.push(`EPI obrigatório faltando: sim (${missingLabels.join(', ')})`);
                        } else if (jev && jev.any_missing_required_ppe === true) {
                            parts.push('EPI obrigatório faltando: sim');
                        } else if (jev && jev.any_missing_required_ppe === false) {
                            parts.push('EPI obrigatório faltando: não');
                        }
                        if (jev && typeof jev === 'object') {
                            Object.entries(jev).forEach(([key, value]) => {
                                if (key === 'any_missing_required_ppe') {
                                    return;
                                }
                                const label = jevLabels[key] || key;
                                const text = value === true ? 'sim' : value === false ? 'não' : String(value);
                                parts.push(`${label}: ${text}`);
                            });
                        }
                        decisions.textContent = parts.join(' · ');
                    } else if (payload.state && payload.state.jev_error) {
                        decisions.textContent = 'Jev sem resposta neste quadro';
                    }
                    applyZoneDwell((payload.state && payload.state.zone_dwell) || []);
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

            const canvas = document.getElementById('zone-canvas');
            const ctx = canvas.getContext('2d');
            const zones = @json($zones);
            const dwellByName = {};
            let drawing = false;
            let draft = [];
            const csrf = document.querySelector('meta[name="csrf-token"]').content;

            function imageBox() {
                const rect = frame.getBoundingClientRect();
                const nw = frame.naturalWidth || 640;
                const nh = frame.naturalHeight || 360;
                const scale = Math.min(rect.width / nw, rect.height / nh);
                const width = nw * scale;
                const height = nh * scale;
                return {
                    left: rect.left + (rect.width - width) / 2,
                    top: rect.top + (rect.height - height) / 2,
                    width, height, nw, nh, scale,
                };
            }

            function resizeCanvas() {
                const stage = document.getElementById('live-stage');
                canvas.width = stage.clientWidth;
                canvas.height = stage.clientHeight;
                paint();
            }

            function toFrame(event) {
                const box = imageBox();
                const x = (event.clientX - box.left) / box.scale;
                const y = (event.clientY - box.top) / box.scale;
                if (x < 0 || y < 0 || x > box.nw || y > box.nh) {
                    return null;
                }
                return [Math.round(x), Math.round(y)];
            }

            function toCanvas(point) {
                const box = imageBox();
                const stage = document.getElementById('live-stage').getBoundingClientRect();
                return [
                    box.left - stage.left + point[0] * box.scale,
                    box.top - stage.top + point[1] * box.scale,
                ];
            }

            function paint() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                const drawPoly = (points, color, title) => {
                    if (!points.length) return;
                    ctx.beginPath();
                    points.forEach((point, index) => {
                        const [x, y] = toCanvas(point);
                        if (index === 0) ctx.moveTo(x, y);
                        else ctx.lineTo(x, y);
                    });
                    ctx.closePath();
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 2;
                    ctx.stroke();
                    ctx.fillStyle = color.replace('1)', '0.18)');
                    ctx.fill();
                    const [x, y] = toCanvas(points[0]);
                    ctx.fillStyle = '#e2e8f0';
                    ctx.font = '13px sans-serif';
                    ctx.fillText(title, x + 6, y + 16);
                };
                zones.forEach((zone) => {
                    drawPoly(zone.polygon || [], zoneStroke(zone), zoneCaption(zone));
                });
                if (draft.length) {
                    drawPoly(draft, 'rgba(250,204,21,1)', 'Nova zona');
                }
            }

            function zoneCaption(zone) {
                const live = dwellByName[zone.name];
                if (live && live.label) {
                    return live.label;
                }
                const kind = zone.type === 'restrita' ? 'Restrita' : 'Passagem';
                const dwell = zone.max_dwell_seconds ? ` · 0s / ${zone.max_dwell_seconds}s` : '';
                return `${zone.name} · ${kind}${dwell}`;
            }

            function zoneStroke(zone) {
                const live = dwellByName[zone.name];
                const restricted = zone.type === 'restrita';
                if (live && (live.exceeded || (live.occupied && restricted))) {
                    return 'rgba(239,68,68,1)';
                }
                if (live && live.occupied) {
                    return 'rgba(251,191,36,1)';
                }
                return restricted ? 'rgba(248,113,113,1)' : 'rgba(52,211,153,1)';
            }

            function escapeHtml(value) {
                return String(value).replace(/[&<>"']/g, (ch) => ({
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#39;',
                }[ch]));
            }

            function applyZoneDwell(items) {
                if (!items.length) {
                    return;
                }
                items.forEach((zone) => {
                    dwellByName[zone.name] = zone;
                });
                const line = document.getElementById('live-zones');
                line.innerHTML = items.map((zone) => {
                    const restricted = zone.type === 'restrita' || zone.type === 'risk';
                    const hot = zone.exceeded || (zone.occupied && restricted);
                    const warm = zone.occupied && !hot;
                    const color = hot ? '#f87171' : warm ? '#fbbf24' : '#94a3b8';
                    const title = restricted ? 'Zona restrita' : 'Permanência em zona';
                    const elapsed = Number(zone.elapsed_s || 0);
                    const clock = zone.max_dwell_seconds ? `${elapsed}s / ${zone.max_dwell_seconds}s` : `${elapsed}s`;
                    const phrase = zone.occupied || zone.exceeded
                        ? `${title}: ${zone.name} (${clock})`
                        : (zone.label || zone.name);
                    return `<span style="color:${color}">${escapeHtml(phrase)}</span>`;
                }).join(' · ');
                document.querySelectorAll('[data-zone-label]').forEach((span) => {
                    const zone = zones.find((item) => item.name === span.dataset.zoneLabel);
                    if (zone) {
                        span.textContent = zoneCaption(zone);
                        span.style.color = zoneStroke(zone).startsWith('rgba(251') ? '#fbbf24' : (zoneStroke(zone).startsWith('rgba(239') || zoneStroke(zone).startsWith('rgba(248') ? '#f87171' : '');
                    }
                });
                paint();
            }

            function renderList() {
                const list = document.getElementById('zone-list');
                list.innerHTML = '';
                zones.forEach((zone) => {
                    const item = document.createElement('li');
                    item.className = 'flex items-center justify-between gap-3';
                    const span = document.createElement('span');
                    span.dataset.zoneLabel = zone.name;
                    span.textContent = zoneCaption(zone);
                    item.appendChild(span);
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'text-red-400';
                    button.textContent = 'Remover';
                    button.addEventListener('click', async () => {
                        await fetch(`/snitch/settings/zones/${zone.id}`, {
                            method: 'DELETE',
                            headers: {'Accept': 'application/json', 'X-CSRF-TOKEN': csrf},
                        });
                        const index = zones.findIndex((item) => item.id === zone.id);
                        if (index >= 0) zones.splice(index, 1);
                        renderList();
                        paint();
                    });
                    item.appendChild(button);
                    list.appendChild(item);
                });
            }

            document.getElementById('zone-draw').addEventListener('click', () => {
                drawing = !drawing;
                document.getElementById('zone-draw').textContent = drawing ? 'Concluir desenho' : 'Desenhar nova zona';
            });
            document.getElementById('zone-undo').addEventListener('click', () => {
                draft.pop();
                paint();
            });
            canvas.addEventListener('click', (event) => {
                if (!drawing) return;
                const point = toFrame(event);
                if (point) {
                    draft.push(point);
                    paint();
                }
            });
            document.getElementById('zone-save').addEventListener('click', async () => {
                if (draft.length < 3) return;
                const body = new FormData();
                body.append('camera_id', @json($camera->id));
                body.append('name', document.getElementById('zone-name').value || 'Zona');
                body.append('type', document.getElementById('zone-type').value);
                const dwell = document.getElementById('zone-dwell').value;
                if (dwell) body.append('max_dwell_seconds', dwell);
                body.append('polygon', JSON.stringify(draft));
                const response = await fetch(@json(route('snitch.settings.zones.store')), {
                    method: 'POST',
                    headers: {'Accept': 'application/json', 'X-CSRF-TOKEN': csrf},
                    body,
                });
                if (!response.ok) return;
                const payload = await response.json();
                zones.push(payload.zone);
                draft = [];
                drawing = false;
                document.getElementById('zone-draw').textContent = 'Desenhar nova zona';
                renderList();
                paint();
            });
            frame.addEventListener('load', () => { resizeCanvas(); });
            window.addEventListener('resize', resizeCanvas);
            renderList();
            resizeCanvas();
        })();
    </script>
@endpush
