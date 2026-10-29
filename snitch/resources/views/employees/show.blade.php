@extends('layouts.snitch')

@section('title', $employee->name)
@section('heading', $employee->name)

@section('breadcrumb')
    <ol class="flex flex-wrap items-center gap-2">
        <li><a href="{{ route('snitch.company.dashboard') }}" class="hover:text-emerald-400">{{ $company->name }}</a></li>
        @if ($location)
            <li class="text-slate-500" aria-hidden="true">/</li>
            <li><a href="{{ route('snitch.locations.show', $location) }}" class="hover:text-emerald-400">{{ $location->name }}</a></li>
        @endif
        <li class="text-slate-500" aria-hidden="true">/</li>
        <li><span class="font-medium text-slate-200" aria-current="page">{{ $employee->name }}</span></li>
    </ol>
@endsection

@section('content')
    <section aria-label="Médias do funcionário" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <article class="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <p class="text-xs uppercase tracking-wide text-slate-400">Média episódios (dia)</p>
            <p class="mt-2 text-3xl font-semibold tabular-nums">{{ $averages['day_avg'] }}</p>
        </article>
        <article class="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <p class="text-xs uppercase tracking-wide text-slate-400">Média episódios (mês)</p>
            <p class="mt-2 text-3xl font-semibold tabular-nums">{{ $averages['month_avg'] }}</p>
        </article>
    </section>

    <div class="grid gap-6 lg:grid-cols-3">
        <section aria-labelledby="photo-heading" class="rounded-xl border border-slate-800 bg-slate-900/40 p-5 lg:col-span-1">
            <h2 id="photo-heading" class="text-lg font-semibold text-white">Foto recente</h2>
            @if ($latestPhoto)
                <img src="{{ $latestPhoto }}" alt="Registro recente de {{ $employee->name }}" class="mt-4 w-full rounded-lg border border-slate-700 object-cover">
            @else
                <p class="mt-4 text-sm text-slate-400">Sem foto registrada.</p>
            @endif
            <p class="mt-3 text-xs text-slate-500">Credencial de câmera não é exibida no histórico (NFR-002).</p>
        </section>

        <section aria-labelledby="attachments-heading" class="rounded-xl border border-slate-800 bg-slate-900/40 p-5 lg:col-span-1">
            <h2 id="attachments-heading" class="text-lg font-semibold text-white">Anexos</h2>
            <ul class="mt-4 space-y-2">
                @forelse ($employee->attachments as $attachment)
                    <li class="rounded-md border border-slate-800 px-3 py-2 text-sm">
                        <span class="font-medium text-slate-200">{{ $attachment->label }}</span>
                        <span class="block truncate text-xs text-slate-500">{{ $attachment->path }}</span>
                    </li>
                @empty
                    <li class="text-sm text-slate-400">Nenhum anexo.</li>
                @endforelse
            </ul>
        </section>

        <section aria-labelledby="history-heading" class="rounded-xl border border-slate-800 bg-slate-900/40 p-5 lg:col-span-1">
            <h2 id="history-heading" class="text-lg font-semibold text-white">Histórico</h2>
            <ul class="mt-4 max-h-96 space-y-3 overflow-y-auto pr-1">
                @forelse ($history as $episode)
                    <li class="rounded-lg border border-slate-800/80 bg-slate-950/40 p-3">
                        <p class="text-sm font-medium capitalize text-slate-100">{{ $episode->type }} · {{ $episode->subtype }}</p>
                        <p class="text-xs text-slate-400">{{ $episode->recorded_at->format('d/m/Y H:i') }}</p>
                    </li>
                @empty
                    <li class="text-sm text-slate-400">Histórico vazio.</li>
                @endforelse
            </ul>
        </section>
    </div>
@endsection
