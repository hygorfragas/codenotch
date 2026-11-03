FROM node:22-bookworm-slim AS assets

WORKDIR /app

COPY snitch/package.json snitch/package-lock.json ./
RUN npm ci

COPY snitch/vite.config.js ./vite.config.js
COPY snitch/resources ./resources
COPY snitch/public ./public

RUN npm run build

FROM php:8.3-cli-bookworm

WORKDIR /var/www/html

RUN apt-get update \
    && apt-get install -y --no-install-recommends unzip git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

COPY snitch/ /var/www/html/

RUN cp .env.example .env \
    && composer install --no-interaction --prefer-dist --no-progress \
    && rm -f .env

COPY --from=assets /app/public/build /var/www/html/public/build

COPY docker/web/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p storage/framework/cache/data storage/framework/sessions storage/framework/views storage/logs bootstrap/cache \
    && chmod -R a+rwx storage bootstrap/cache

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
