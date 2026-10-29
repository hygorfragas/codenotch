<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield('title', 'SNITCH') — Encarregado Virtual</title>
    @vite(['resources/css/app.css', 'resources/js/app.js'])
</head>
<body class="min-h-screen bg-slate-950 text-slate-100 antialiased">
    <div class="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <header class="mb-6 flex flex-col gap-4 border-b border-slate-800 pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
                <p class="text-xs font-semibold uppercase tracking-wider text-emerald-400">SNITCH</p>
                <h1 class="text-xl font-semibold text-white sm:text-2xl">@yield('heading')</h1>
            </div>
            <nav aria-label="Menu principal" class="flex flex-wrap gap-2 text-sm">
                <a href="{{ route('snitch.company.dashboard') }}"
                   class="rounded-md px-3 py-2 {{ request()->routeIs('snitch.company.dashboard') ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-900' }}">
                    Painel global
                </a>
                @isset($company)
                    <span class="hidden items-center text-slate-500 sm:flex" aria-hidden="true">/</span>
                    <span class="rounded-md px-3 py-2 text-slate-400">{{ $company->name }}</span>
                @endisset
            </nav>
        </header>

        @hasSection('breadcrumb')
            <nav aria-label="Breadcrumb" class="mb-4 text-sm text-slate-400">
                @yield('breadcrumb')
            </nav>
        @endif

        <main class="flex-1 space-y-6">
            @yield('content')
        </main>
    </div>
    @stack('scripts')
</body>
</html>
