@props(['day', 'month', 'dayLabel' => 'Episódios hoje', 'monthLabel' => 'Episódios no mês'])

<section aria-label="Indicadores do período" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <article class="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
        <p class="text-xs font-medium uppercase tracking-wide text-slate-400">{{ $dayLabel }}</p>
        <p class="mt-2 text-3xl font-semibold tabular-nums text-white">{{ $day }}</p>
    </article>
    <article class="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
        <p class="text-xs font-medium uppercase tracking-wide text-slate-400">{{ $monthLabel }}</p>
        <p class="mt-2 text-3xl font-semibold tabular-nums text-white">{{ $month }}</p>
    </article>
</section>
