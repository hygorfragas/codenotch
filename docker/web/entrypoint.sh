#!/bin/sh
set -eu

cd /var/www/html

mkdir -p /data \
    storage/framework/cache/data \
    storage/framework/sessions \
    storage/framework/views \
    storage/logs \
    bootstrap/cache

touch /data/database.sqlite

if [ ! -s /data/app.key ]; then
    php -r 'echo "base64:".base64_encode(random_bytes(32));' > /data/app.key
fi

APP_KEY="$(tr -d '\r\n' < /data/app.key)"

# Arquivo, não environment do container: o Pest (--env=testing) não herda o banco de demo.
cat > .env <<EOF
APP_NAME=SNITCH
APP_ENV=local
APP_KEY=${APP_KEY}
APP_DEBUG=true
APP_URL=http://127.0.0.1:8000
APP_LOCALE=pt_BR
APP_FALLBACK_LOCALE=pt_BR
APP_FAKER_LOCALE=pt_BR
APP_MAINTENANCE_DRIVER=file
BCRYPT_ROUNDS=12
LOG_CHANNEL=stderr
LOG_LEVEL=debug
DB_CONNECTION=sqlite
DB_DATABASE=/data/database.sqlite
SESSION_DRIVER=database
SESSION_LIFETIME=120
SESSION_ENCRYPT=false
SESSION_PATH=/
BROADCAST_CONNECTION=log
FILESYSTEM_DISK=local
QUEUE_CONNECTION=database
CACHE_STORE=database
MAIL_MAILER=log
SNITCH_ENGINE_URL=http://host.docker.internal:8765
SNITCH_ENGINE_PUBLIC_URL=http://127.0.0.1:8765
SH17_WEIGHTS=/weights/sh17.pt
JEV_URL=http://host.docker.internal:8787
EOF

export PHP_CLI_SERVER_WORKERS="${PHP_CLI_SERVER_WORKERS:-8}"

php -r '$pdo = new PDO("sqlite:/data/database.sqlite"); $pdo->exec("PRAGMA journal_mode=WAL;");'

php artisan migrate --force --no-interaction
php artisan db:seed --class=Database\\Seeders\\SnitchDemoSeeder --force --no-interaction

exec php -d output_buffering=0 -d implicit_flush=1 \
    artisan serve --host=0.0.0.0 --port=8000 --no-reload
