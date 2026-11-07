# Aplicação e implementações

<!-- specsfy:documentator:start -->
## Superfícies

Categorias: Serviços, Rotas e APIs, Páginas, Componentes, Testes e Outras fontes.

Relação: relaciona cada arquivo observado à sua superfície.

| Categoria | Arquivo | Símbolos |
| --- | --- | --- |
| Páginas | snitch/app/Contracts/VisionEngine.php | VisionEngine, isHealthy, streamLiveFrames |
| Páginas | snitch/app/Enums/EpisodeType.php | EpisodeType |
| Páginas | snitch/app/Enums/UserRole.php | UserRole |
| Páginas | snitch/app/Enums/ZoneType.php | ZoneType |
| Páginas | snitch/app/Http/Controllers/Controller.php | Controller |
| Páginas | snitch/app/Http/Controllers/LiveCameraController.php | LiveCameraController, __construct, show, panel, stream |
| Páginas | snitch/app/Http/Controllers/LocationCameraController.php | LocationCameraController, index |
| Páginas | snitch/app/Http/Controllers/Snitch/AlertController.php | AlertController, __construct, store |
| Páginas | snitch/app/Http/Controllers/Snitch/CompanyDashboardController.php | CompanyDashboardController, __construct, __invoke |
| Páginas | snitch/app/Http/Controllers/Snitch/EmployeeProfileController.php | EmployeeProfileController, __construct, show |
| Páginas | snitch/app/Http/Controllers/Snitch/EpisodeController.php | EpisodeController, __construct, missingPpe, idleZone, smartphone |
| Páginas | snitch/app/Http/Controllers/Snitch/LocationApiController.php | LocationApiController, cameras |
| Páginas | snitch/app/Http/Controllers/Snitch/LocationDashboardController.php | LocationDashboardController, __construct, show |
| Páginas | snitch/app/Models/Alert.php | Alert, casts, syncDispatchPresentation, getOnPanelAttribute, getExternalDispatchesAttribute, episode |
| Páginas | snitch/app/Models/Camera.php | Camera, booted, location, zones, trackerLinks, episodes, credential |
| Páginas | snitch/app/Models/Company.php | Company, locations, employees, episodes, users |
| Páginas | snitch/app/Models/Employee.php | Employee, company, episodes, attachments, trackerLinks |
| Páginas | snitch/app/Models/EmployeeAttachment.php | EmployeeAttachment, employee |
| Páginas | snitch/app/Models/Episode.php | Episode, casts, company, location, employee, camera, zone, alerts |
| Páginas | snitch/app/Models/Location.php | Location, company, cameras, episodes, ppeRequirements, smartphoneSetting, alertChannels, managers |
| Páginas | snitch/app/Models/LocationAlertChannel.php | LocationAlertChannel, casts, location |
| Páginas | snitch/app/Models/LocationPpeRequirement.php | LocationPpeRequirement, casts, location |
| Páginas | snitch/app/Models/LocationSmartphoneSetting.php | LocationSmartphoneSetting, casts, location |
| Páginas | snitch/app/Models/TrackerLink.php | TrackerLink, casts, camera, employee |
| Páginas | snitch/app/Models/User.php | User, casts, company, location |
| Páginas | snitch/app/Models/Zone.php | Zone, casts, camera, episodes |
| Páginas | snitch/app/Providers/AppServiceProvider.php | AppServiceProvider, register, boot |
| Páginas | snitch/app/Providers/SnitchServiceProvider.php | SnitchServiceProvider, register, boot |
| Serviços | snitch/app/Services/AlertDispatcher.php | AlertDispatcher, IDLE_ONLY_CHANNELS, dispatch, resolveEpisodeId, resolveExternalDispatches, shouldSkipExternalChannel |
| Serviços | snitch/app/Services/DashboardQuery.php | DashboardQuery, defaultCompany, episodeTotals, anonymousRecentEpisodes, locationTotals, locationEpisodesWithEmployee, employeeAverages, employeeHistory |
| Serviços | snitch/app/Services/EpisodeRecorder.php | EpisodeRecorder, recordMissingPpe, recordIdleZone, recordSmartphone, persistEpisode, resolveCompanyAndLocation, capturePhotoReference, episodeResponse |
| Serviços | snitch/app/Services/HttpVisionEngine.php | HttpVisionEngine, isHealthy, streamLiveFrames |
| Outras fontes | snitch/bootstrap/app.php | — |
| Outras fontes | snitch/bootstrap/cache/packages.php | — |
| Outras fontes | snitch/bootstrap/cache/services.php | — |
| Outras fontes | snitch/bootstrap/providers.php | — |
| Outras fontes | snitch/config/app.php | — |
| Outras fontes | snitch/config/auth.php | — |
| Outras fontes | snitch/config/cache.php | — |
| Outras fontes | snitch/config/database.php | — |
| Outras fontes | snitch/config/filesystems.php | — |
| Outras fontes | snitch/config/logging.php | — |
| Outras fontes | snitch/config/mail.php | — |
| Outras fontes | snitch/config/queue.php | — |
| Outras fontes | snitch/config/services.php | — |
| Outras fontes | snitch/config/session.php | — |
| Outras fontes | snitch/config/snitch.php | — |
| Outras fontes | snitch/database/factories/CameraFactory.php | CameraFactory, definition |
| Outras fontes | snitch/database/factories/CompanyFactory.php | CompanyFactory, definition |
| Outras fontes | snitch/database/factories/EmployeeFactory.php | EmployeeFactory, definition |
| Outras fontes | snitch/database/factories/EpisodeFactory.php | EpisodeFactory, definition |
| Outras fontes | snitch/database/factories/LocationFactory.php | LocationFactory, definition |
| Outras fontes | snitch/database/factories/UserFactory.php | UserFactory, definition, unverified |
| Outras fontes | snitch/database/migrations/0001_01_01_000000_create_users_table.php | extends, up, down |
| Outras fontes | snitch/database/migrations/0001_01_01_000001_create_cache_table.php | extends, up, down |
| Outras fontes | snitch/database/migrations/0001_01_01_000002_create_jobs_table.php | extends, up, down |
| Outras fontes | snitch/database/migrations/2026_10_28_000001_create_snitch_tables.php | extends, up, down |
| Outras fontes | snitch/database/seeders/DatabaseSeeder.php | DatabaseSeeder, run |
| Outras fontes | snitch/database/seeders/SnitchDemoSeeder.php | SnitchDemoSeeder, run |
| Outras fontes | snitch/engine/analyze_stream.py | ZoneConfig, AnalyzeStreamConfig, StreamAnalyzer |
| Outras fontes | snitch/engine/jev_client.py | — |
| Outras fontes | snitch/engine/sse_server.py | — |
| Outras fontes | snitch/engine/state_builder.py | TrackedPerson |
| Outras fontes | snitch/public/index.php | — |
| Outras fontes | snitch/resources/css/app.css | — |
| Outras fontes | snitch/resources/js/app.js | — |
| Páginas | snitch/resources/views/cameras/live.blade.php | showError |
| Páginas | snitch/resources/views/company/dashboard.blade.php | — |
| Páginas | snitch/resources/views/components/kpi-strip.blade.php | — |
| Páginas | snitch/resources/views/employees/show.blade.php | — |
| Páginas | snitch/resources/views/layouts/snitch.blade.php | — |
| Páginas | snitch/resources/views/locations/show.blade.php | — |
| Páginas | snitch/resources/views/welcome.blade.php | — |
| Rotas e APIs | snitch/routes/console.php | — |
| Rotas e APIs | snitch/routes/snitch.php | — |
| Rotas e APIs | snitch/routes/web.php | — |
| Outras fontes | snitch/vite.config.js | — |
| Outras fontes | windows/codenotch/build.rs | — |
| Outras fontes | windows/codenotch/src/activity.rs | INTERVAL, ANTIGRAVITY_STALE_MS, call, CodexStep, CLAUDE_RATE_BPS, CLAUDE_HOLD_MS |
| Outras fontes | windows/codenotch/src/agy_cli.rs | — |
| Outras fontes | windows/codenotch/src/antigravity.rs | POLL_SECS, CLI_TTL, LOAD_CODE_ASSIST, QUOTA_SUMMARY, LS_SERVICE, CSRF_HEADER |
| Outras fontes | windows/codenotch/src/autostart.rs | RUN_KEY, NAME |
| Outras fontes | windows/codenotch/src/claude_auth.rs | LOGIN_SCRIPT |
| Outras fontes | windows/codenotch/src/codex.rs | POLL_SECS, TAIL_BYTES, CURRENT_FOR_MS, ENDPOINT, BACKOFF_MIN_SECS, NATIVE_STAND_DOWN_MS, LiveErr |
| Outras fontes | windows/codenotch/src/config.rs | SIZES, EDGES |
| Outras fontes | windows/codenotch/src/cursor.rs | ENDPOINT, POLL_SECS, FetchErr |
| Outras fontes | windows/codenotch/src/diag.rs | SECRET |
| Outras fontes | windows/codenotch/src/doctor.rs | — |
| Outras fontes | windows/codenotch/src/dropzones.rs | LABEL |
| Outras fontes | windows/codenotch/src/focus.rs | — |
| Outras fontes | windows/codenotch/src/glm.rs | POLL_SECS, BACKOFF_BASE_SECS, BACKOFF_CAP_SECS, FetchErr |
| Outras fontes | windows/codenotch/src/glyphs.rs | IDS, BUILTIN, T, SIZE |
| Outras fontes | windows/codenotch/src/grok.rs | ENDPOINT, POLL_SECS, TRUSTED_ISSUER, FetchErr |
| Outras fontes | windows/codenotch/src/hooks_install.rs | WIRING |
| Outras fontes | windows/codenotch/src/i18n.rs | RUSSIAN_KEYS, UKRAINIAN_KEYS, TRADITIONAL_CHINESE_KEYS |
| Outras fontes | windows/codenotch/src/main.rs | NOTCH_W, BUILD, NOTCH_H, NOTCH_UPRIGHT_H, LANDING_FALLBACK_MS, WORK_AREA_POLL_MS, RUN_LOG_MAX_BYTES, HOT_PAD |
| Outras fontes | windows/codenotch/src/notchmenu.rs | PREFIX |
| Outras fontes | windows/codenotch/src/server.rs | — |
| Outras fontes | windows/codenotch/src/settings_window.rs | LABEL, FIRST_MICA_BUILD |
| Outras fontes | windows/codenotch/src/state.rs | ST_RUNNING, ST_ATTENTION, ST_DONE, ST_IDLE, RUNNING_STALE_MS, DONE_STALE_MS, IDLE_DROP_MS, ATTENTION_STALE_MS |
| Outras fontes | windows/codenotch/src/tray.rs | — |
| Outras fontes | windows/codenotch/src/trayicon.rs | T |
| Outras fontes | windows/codenotch/src/traymenu.rs | MIN |
| Outras fontes | windows/codenotch/src/updater.rs | UNSET_PUBKEY |
| Outras fontes | windows/codenotch/src/usage.rs | ENDPOINT, POLL_ACTIVE_SECS, POLL_IDLE_SECS, BACKOFF_BASE_SECS, BACKOFF_CAP_SECS, RENEW_MARGIN_MS, RENEW_COOLDOWN_MS, RENEW_RETRY_CAP_MS |
| Outras fontes | windows/codenotch/src/watcher.rs | QUIET_DONE_MS, QUIET_ATTN_MS, QUIET_USER_DONE_MS, RESCAN_SECS, FRESH_WINDOW_MS, TAIL_BYTES, Kind, INGEST_MIN_GAP |
| Outras fontes | windows/codenotch-hook/src/main.rs | DEFAULT_PORT, MAX_STDIN, DETACHED_PROCESS, CREATE_NO_WINDOW |
| Outras fontes | windows/scripts/check-ui-scripts.mjs | body |
| Outras fontes | windows/scripts/test-claude-auth-ui.cjs | — |
| Outras fontes | windows/test-codex-headline.cjs | markedSource, order, staleOf |
<!-- specsfy:documentator:end -->
