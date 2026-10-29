@extends('layouts.snitch')

@section('title', 'Painel global')
@section('heading', 'Painel global da empresa')

@section('breadcrumb')
    <ol class="flex flex-wrap items-center gap-2">
        <li><span class="font-medium text-slate-200" aria-current="page">{{ $company->name }}</span></li>
        <li class="text-slate-500" aria-hidden="true">/</li>
        <li><span class="text-slate-300">Painel global</span></li>
    </ol>
@endsection

@section('content')
    <x-kpi-strip :day="$totals['day']" :month="$totals['month']" />

    <div class="grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="locations-heading" class="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
            <h2 id="locations-heading" class="text-lg font-semibold text-white">Localidades</h2>
            <p class="mt-1 text-sm text-slate-400">Abra uma localidade para câmeras, episódios e funcionários.</p>
            <ul class="mt-4 divide-y divide-slate-800">
                @forelse ($locations as $location)
                    <li class="flex items-center justify-between gap-3 py-3">
                        <div>
                            <p class="font-medium text-slate-100">{{ $location->name }}</p>
                            <p class="text-xs text-slate-500">ID {{ $location->id }}</p>
                        </div>
                        <a href="{{ route('snitch.locations.show', $location) }}"
                           class="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500">
                            Abrir
                        </a>
                    </li>
                @empty
                    <li class="py-6 text-sm text-slate-400">Nenhuma localidade cadastrada.</li>
                @endforelse
            </ul>
        </section>

        <section aria-labelledby="episodes-heading" class="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
            <h2 id="episodes-heading" class="text-lg font-semibold text-white">Episódios recentes</h2>
            <p class="mt-1 text-sm text-slate-400">Sem identificação do colaborador (visão global).</p>
            <ul class="mt-4 space-y-3">
                @forelse ($episodes as $episode)
                    <li class="flex gap-3 rounded-lg border border-slate-800/80 bg-slate-950/40 p-3">
                        @if ($episode->photo)
                            <img src="{{ $episode->photo }}" alt="" class="h-14 w-24 shrink-0 rounded object-cover" loading="lazy">
                        @endif
                        <div class="min-w-0 flex-1">
                            <p class="text-sm font-medium capitalize text-slate-100">{{ $episode->type }} · {{ $episode->subtype }}</p>
                            <p class="text-xs text-slate-400">{{ $episode->recorded_at->timezone(config('app.timezone'))->format('d/m/Y H:i') }}</p>
                            <p class="truncate text-xs text-slate-500">Localidade #{{ $episode->location_id }}</p>
                        </div>
                    </li>
                @empty
                    <li class="py-6 text-sm text-slate-400">Nenhum episódio registrado hoje.</li>
                @endforelse
            </ul>
        </section>
    </div>
@endsection
