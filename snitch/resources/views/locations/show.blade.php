@extends('layouts.snitch')

@section('title', $location->name)
@section('heading', $location->name)

@section('breadcrumb')
    <ol class="flex flex-wrap items-center gap-2">
        <li><a href="{{ route('snitch.company.dashboard') }}" class="hover:text-emerald-400">{{ $company->name }}</a></li>
        <li class="text-slate-500" aria-hidden="true">/</li>
        <li><span class="font-medium text-slate-200" aria-current="page">{{ $location->name }}</span></li>
    </ol>
@endsection

@section('content')
    <x-kpi-strip :day="$totals['day']" :month="$totals['month']" />

    <nav aria-label="Menu da localidade" class="flex flex-wrap gap-2 text-sm">
        <span class="rounded-md bg-slate-800 px-3 py-1.5 text-white">Câmeras</span>
        <span class="rounded-md px-3 py-1.5 text-slate-400">Episódios</span>
        <span class="rounded-md px-3 py-1.5 text-slate-400">Funcionários</span>
    </nav>

    <div class="grid gap-6 xl:grid-cols-3">
        <section aria-labelledby="cameras-heading" class="rounded-xl border border-slate-800 bg-slate-900/40 p-5 xl:col-span-1">
            <h2 id="cameras-heading" class="text-lg font-semibold text-white">Câmeras</h2>
            <ul class="mt-4 space-y-3">
                @forelse ($cameras as $camera)
                    <li class="rounded-lg border border-slate-800 p-3">
                        <p class="font-medium text-slate-100">{{ $camera->name }}</p>
                        <p class="text-xs text-slate-500">{{ $camera->sector ?? 'Setor não informado' }}</p>
                        <a href="{{ route('snitch.cameras.live.view', $camera) }}"
                           class="mt-2 inline-flex text-sm font-medium text-emerald-400 hover:text-emerald-300">
                            Ver ao vivo
                        </a>
                    </li>
                @empty
                    <li class="py-4 text-sm text-slate-400">Lista vazia — nenhuma câmera nesta localidade.</li>
                @endforelse
            </ul>
        </section>

        <section aria-labelledby="location-episodes-heading" class="rounded-xl border border-slate-800 bg-slate-900/40 p-5 xl:col-span-1">
            <h2 id="location-episodes-heading" class="text-lg font-semibold text-white">Episódios</h2>
            <ul class="mt-4 space-y-3">
                @forelse ($episodes as $episode)
                    <li class="rounded-lg border border-slate-800/80 bg-slate-950/40 p-3">
                        <p class="text-sm font-medium text-slate-100">
                            {{ $episode->employee?->name ?? 'Sem vínculo' }}
                            <span class="text-slate-500">·</span>
                            <span class="capitalize">{{ $episode->type }}</span>
                        </p>
                        <p class="text-xs text-slate-400">{{ $episode->recorded_at->format('d/m/Y H:i') }}</p>
                    </li>
                @empty
                    <li class="py-4 text-sm text-slate-400">Nenhum episódio recente.</li>
                @endforelse
            </ul>
        </section>

        <section aria-labelledby="employees-heading" class="rounded-xl border border-slate-800 bg-slate-900/40 p-5 xl:col-span-1">
            <h2 id="employees-heading" class="text-lg font-semibold text-white">Funcionários</h2>
            <ul class="mt-4 divide-y divide-slate-800">
                @forelse ($employees as $employee)
                    <li class="flex items-center justify-between gap-2 py-3">
                        <div>
                            <p class="font-medium text-slate-100">{{ $employee->name }}</p>
                            <p class="text-xs text-slate-500">ID {{ $employee->id }}</p>
                        </div>
                        <a href="{{ route('snitch.employees.show', $employee) }}"
                           class="text-sm font-medium text-emerald-400 hover:text-emerald-300">
                            Perfil
                        </a>
                    </li>
                @empty
                    <li class="py-4 text-sm text-slate-400">Nenhum funcionário vinculado.</li>
                @endforelse
            </ul>
        </section>
    </div>
@endsection
