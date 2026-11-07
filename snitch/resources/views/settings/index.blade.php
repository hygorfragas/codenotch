@extends('layouts.snitch')

@section('title', 'Configurações')
@section('heading', 'Configurações')

@section('content')
    @if (session('status'))
        <p class="rounded-lg border border-emerald-800 bg-emerald-950/40 px-4 py-3 text-sm text-emerald-300" role="status">{{ session('status') }}</p>
    @endif
    @if ($errors->any())
        <div class="rounded-lg border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-300" role="alert">
            @foreach ($errors->all() as $error)
                <p>{{ $error }}</p>
            @endforeach
        </div>
    @endif

    <x-engine-status />

    @if (! $company)
        <p class="text-sm text-slate-400">Nenhuma empresa cadastrada.</p>
    @else
        <p class="text-sm text-slate-400">Empresa: <span class="text-slate-200">{{ $company->name }}</span></p>

        @foreach ($company->locations as $location)
            <section class="space-y-6 rounded-xl border border-slate-800 bg-slate-900/30 p-5">
                <h2 class="text-lg font-semibold text-white">{{ $location->name }}</h2>

                <form method="post" action="{{ route('snitch.settings.ppe') }}" class="space-y-3">
                    @csrf
                    <input type="hidden" name="location_id" value="{{ $location->id }}">
                    <h3 class="text-sm font-semibold text-slate-200">EPI obrigatório</h3>
                    <div class="flex flex-wrap gap-3">
                        @foreach ($ppeCategories as $category => $label)
                            @php $on = (bool) $location->ppeRequirements->firstWhere('category', $category)?->required; @endphp
                            <label class="flex items-center gap-2 text-sm text-slate-300">
                                <input type="checkbox" name="categories[]" value="{{ $category }}" @checked($on) class="rounded border-slate-600 bg-slate-950">
                                {{ $label }}
                            </label>
                        @endforeach
                    </div>
                    <button class="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white">Salvar EPI</button>
                </form>

                <form method="post" action="{{ route('snitch.settings.smartphone') }}" class="flex flex-wrap items-end gap-3">
                    @csrf
                    <input type="hidden" name="location_id" value="{{ $location->id }}">
                    <h3 class="w-full text-sm font-semibold text-slate-200">Uso de smartphone</h3>
                    <p class="w-full text-xs text-slate-500">A infração só nasce depois do tempo mínimo, com o uso confirmado.</p>
                    <label class="flex items-center gap-2 text-sm text-slate-300">
                        <input type="checkbox" name="enabled" value="1" @checked($location->smartphoneSetting?->enabled) class="rounded border-slate-600 bg-slate-950">
                        Ativo
                    </label>
                    <label class="text-sm text-slate-300">
                        Tempo mínimo para infração (segundos)
                        <input type="number" name="hand_limit_seconds" min="1" value="{{ $location->smartphoneSetting?->hand_limit_seconds }}" class="mt-1 block w-32 rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                    </label>
                    <button class="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white">Salvar</button>
                </form>

                <div>
                    <h3 class="text-sm font-semibold text-slate-200">Canais de alerta</h3>
                    <p class="mt-1 text-xs text-slate-500">O painel ao vivo permanece ativo. Os canais abaixo são extras.</p>
                    <div class="mt-3 space-y-2">
                        @foreach ($episodeTypes as $typeKey => $typeLabel)
                            @foreach ($extraChannels as $channelKey => $channelLabel)
                                @php $row = $location->alertChannels->first(fn ($ch) => $ch->episode_type === $typeKey && $ch->channel === $channelKey); @endphp
                                <form method="post" action="{{ route('snitch.settings.alerts') }}" class="flex flex-wrap items-center gap-3 text-sm">
                                    @csrf
                                    <input type="hidden" name="location_id" value="{{ $location->id }}">
                                    <input type="hidden" name="episode_type" value="{{ $typeKey }}">
                                    <input type="hidden" name="channel" value="{{ $channelKey }}">
                                    <span class="w-40 text-slate-300">{{ $typeLabel }}</span>
                                    <span class="w-24 text-slate-400">{{ $channelLabel }}</span>
                                    <label class="flex items-center gap-2 text-slate-300">
                                        <input type="checkbox" name="enabled" value="1" @checked($row?->enabled) class="rounded border-slate-600 bg-slate-950">
                                        Ativo
                                    </label>
                                    <button class="rounded-md border border-slate-700 px-2 py-1 text-slate-200">Salvar</button>
                                </form>
                            @endforeach
                        @endforeach
                    </div>
                </div>

                <div class="space-y-4">
                    <h3 class="text-sm font-semibold text-slate-200">Câmeras e zonas</h3>
                    @foreach ($location->cameras as $camera)
                        <article class="rounded-lg border border-slate-800 p-4">
                            <form method="post" action="{{ route('snitch.settings.cameras.update', $camera) }}" class="grid gap-3 md:grid-cols-2">
                                @csrf
                                @method('put')
                                <label class="text-sm text-slate-300">Nome
                                    <input name="name" value="{{ $camera->name }}" required class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                                </label>
                                <label class="text-sm text-slate-300">Setor
                                    <input name="sector" value="{{ $camera->sector }}" class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                                </label>
                                <label class="text-sm text-slate-300 md:col-span-2">Stream
                                    <input name="stream_url" value="{{ $camera->stream_url }}" required class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                                </label>
                                <label class="text-sm text-slate-300 md:col-span-2">DVR
                                    <input name="dvr_url" value="{{ $camera->dvr_url }}" class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                                </label>
                                <button class="w-fit rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white">Salvar câmera</button>
                            </form>

                            <ul class="mt-4 space-y-2 text-sm text-slate-300">
                                @forelse ($camera->zones as $zone)
                                    <li class="flex items-center justify-between gap-3">
                                        <span>{{ $zone->name }} · {{ $zone->type->value }} @if($zone->max_dwell_seconds) · {{ $zone->max_dwell_seconds }}s @endif</span>
                                        <form method="post" action="{{ route('snitch.settings.zones.destroy', $zone) }}">
                                            @csrf
                                            @method('delete')
                                            <button class="text-red-400">Remover</button>
                                        </form>
                                    </li>
                                @empty
                                    <li class="text-slate-500">Nenhuma zona.</li>
                                @endforelse
                            </ul>

                            <form method="post" action="{{ route('snitch.settings.zones.store') }}" class="mt-3 grid gap-3 md:grid-cols-2">
                                @csrf
                                <input type="hidden" name="camera_id" value="{{ $camera->id }}">
                                <label class="text-sm text-slate-300">Nova zona
                                    <input name="name" required class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                                </label>
                                <label class="text-sm text-slate-300">Tipo
                                    <select name="type" class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                                        <option value="passagem">passagem</option>
                                        <option value="restrita">restrita</option>
                                    </select>
                                </label>
                                <label class="text-sm text-slate-300">Permanência máxima (s)
                                    <input type="number" name="max_dwell_seconds" min="1" class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                                </label>
                                <label class="text-sm text-slate-300 md:col-span-2">Polígono JSON
                                    <textarea name="polygon" rows="2" required class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1">[[100,100],[500,100],[500,400],[100,400]]</textarea>
                                </label>
                                <button class="w-fit rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-100">Criar zona</button>
                            </form>

                            <div class="mt-4 space-y-2 text-sm">
                                @foreach ($camera->trackerLinks as $link)
                                    <div class="flex items-center justify-between gap-3">
                                        <span class="text-slate-300">Track #{{ $link->tracker_id }} → {{ $link->employee?->name ?? 'sem nome' }}</span>
                                        <form method="post" action="{{ route('snitch.settings.tracker-links.destroy', $link) }}">
                                            @csrf
                                            @method('delete')
                                            <button class="text-red-400">Desvincular</button>
                                        </form>
                                    </div>
                                @endforeach
                                <form method="post" action="{{ route('snitch.settings.tracker-links.store') }}" class="flex flex-wrap items-end gap-2">
                                    @csrf
                                    <input type="hidden" name="camera_id" value="{{ $camera->id }}">
                                    <label class="text-slate-300">Track
                                        <input type="number" name="tracker_id" min="1" required class="mt-1 block w-24 rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                                    </label>
                                    <label class="text-slate-300">Colaborador
                                        <select name="employee_id" required class="mt-1 block rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                                            @foreach ($company->employees as $employee)
                                                <option value="{{ $employee->id }}">{{ $employee->name }}</option>
                                            @endforeach
                                        </select>
                                    </label>
                                    <button class="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white">Vincular</button>
                                </form>
                            </div>
                        </article>
                    @endforeach

                    <form method="post" action="{{ route('snitch.settings.cameras.store') }}" class="grid gap-3 rounded-lg border border-dashed border-slate-700 p-4 md:grid-cols-2">
                        @csrf
                        <input type="hidden" name="location_id" value="{{ $location->id }}">
                        <h3 class="md:col-span-2 text-sm font-semibold text-slate-200">Nova câmera</h3>
                        <label class="text-sm text-slate-300">Nome<input name="name" required class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1"></label>
                        <label class="text-sm text-slate-300">Setor<input name="sector" class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1"></label>
                        <label class="text-sm text-slate-300 md:col-span-2">Stream<input name="stream_url" required class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1"></label>
                        <label class="text-sm text-slate-300 md:col-span-2">DVR<input name="dvr_url" class="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1"></label>
                        <button class="w-fit rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white">Adicionar câmera</button>
                    </form>
                </div>
            </section>
        @endforeach

        <section class="rounded-xl border border-slate-800 p-5">
            <h2 class="text-lg font-semibold text-white">Novo colaborador</h2>
            <form method="post" action="{{ route('snitch.settings.employees.store') }}" enctype="multipart/form-data" class="mt-3 flex flex-wrap items-end gap-3">
                @csrf
                <input type="hidden" name="company_id" value="{{ $company->id }}">
                <label class="text-sm text-slate-300">Nome
                    <input name="name" required class="mt-1 block rounded-md border border-slate-700 bg-slate-950 px-2 py-1">
                </label>
                <label class="text-sm text-slate-300">Foto
                    <input type="file" name="photo" accept="image/*" class="mt-1 block text-sm">
                </label>
                <button class="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white">Criar</button>
            </form>
            <ul class="mt-4 space-y-1 text-sm text-slate-300">
                @foreach ($company->employees as $employee)
                    <li>{{ $employee->name }}</li>
                @endforeach
            </ul>
        </section>
    @endif
@endsection
